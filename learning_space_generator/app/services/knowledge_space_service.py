import json
import pandas as pd
from collections import deque
from learning_space_generator.app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class KnowledgeSpaceService:
    def load_implications(self):
        if not settings.IMPLICATIONS_FILE.exists():
            raise FileNotFoundError("Implications file not found.")
        with open(settings.IMPLICATIONS_FILE, 'r') as f:
            return json.load(f)

    def load_items(self):
         # Try loading from cleaned data for full list, fallback to implications
        if settings.CLEANED_DATA_FILE.exists():
            df = pd.read_csv(settings.CLEANED_DATA_FILE)
            return sorted(df.columns.tolist())
        else:
             # This fallback is weaker but prevents crash if csv missing
            implications = self.load_implications()
            items = set()
            for edge in implications:
                items.add(edge['source'])
                items.add(edge['target'])
            return sorted(list(items))

    def generate_states(self):
        implications = self.load_implications()
        items = self.load_items()
        
        # Build prerequisites map (reverse graph)
        prereqs = {item: set() for item in items}
        for edge in implications:
            prereqs[edge['target']].add(edge['source'])
        
        # Load student data to compute state frequency
        try:
            student_data = pd.read_csv(settings.CLEANED_DATA_FILE)
            student_states = []
            for _, row in student_data.iterrows():
                state = frozenset(col for col in student_data.columns if row[col] == 1)
                student_states.append(state)
            state_frequency = {}
            for state in student_states:
                state_frequency[state] = state_frequency.get(state, 0) + 1
            total_students = len(student_data)
            observed_states = set(state_frequency.keys())
            logger.info(f"Loaded {len(observed_states)} unique observed states from {total_students} students.")
        except Exception as e:
            logger.warning(f"Could not load student data for frequency analysis ({e}). Using equal weights.")
            state_frequency = {}
            observed_states = set()
            total_students = 1
            
        initial_state = frozenset()
        ks_graph = {}
        
        queue = deque([initial_state])
        visited = {initial_state}
        state_probabilities = {}  # Track probability of each state
        
        logger.info("Generating knowledge states with intelligent pruning...")
        
        count = 0 
        while queue:
            current_state = queue.popleft()
            
            # Key generation
            curr_list = sorted(list(current_state))
            if not curr_list:
                curr_key = "{}"
            else:
                curr_key = "{" + ", ".join(curr_list) + "}"
                
            if curr_key not in ks_graph:
                ks_graph[curr_key] = []
                
            # Find successors
            # Item x can be added if x not in current AND prereqs(x) subset of current
            candidates = [
                item for item in items 
                if item not in current_state and prereqs[item].issubset(current_state)
            ]
            
            for item in candidates:
                next_state = current_state | {item}
                
                # INTELLIGENT PRUNING:
                # Include state if:
                # 1. It's observed in student data (frequency >= 1)
                # 2. It's on a path to observed states (partially observed parents)
                freq = state_frequency.get(next_state, 0)
                prob = freq / total_students if total_students > 0 else 0
                
                # Check if state is on path to real states
                on_path = any(
                    next_state.issubset(obs_state) 
                    for obs_state in observed_states
                ) if observed_states else True
                
                # Include if: observed directly OR on path to observed
                if freq >= 1 or on_path:
                    # Next Key
                    next_list = sorted(list(next_state))
                    next_key = "{" + ", ".join(next_list) + "}"
                    
                    ks_graph[curr_key].append(next_key)
                    state_probabilities[next_key] = prob
                    
                    if next_state not in visited:
                        visited.add(next_state)
                        queue.append(next_state)
                        count += 1
                        
                        if count >= settings.MAX_STATES_LIMIT:
                            logger.warning(f"State limit reached ({settings.MAX_STATES_LIMIT}). Stopping generation.")
                            break
                
            if count >= settings.MAX_STATES_LIMIT:
                break
                
        logger.info(f"Generated {len(visited)} states (kept all observed + intermediate states).")
        logger.info(f"Coverage: {len(visited)} states from {len(observed_states)} observed student states.")
        
        with open(settings.KNOWLEDGE_SPACE_FILE, 'w') as f:
            json.dump(ks_graph, f, indent=2)
        logger.info(f"Saved to {settings.KNOWLEDGE_SPACE_FILE}")

knowledge_space_service = KnowledgeSpaceService()
