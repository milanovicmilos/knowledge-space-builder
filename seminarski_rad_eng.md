 
 
 
 
 
 
Seminar Paper 
 
Automated Generation of Knowledge Spaces based on student responses 
 
Architecture and Implementation of a Web Platform 
 
 
 
 
 
 
 
 
	Author: 	 Miloš Milanović 
Subject: Contemporary Educational Technologies and Standards, Semantic Web 
Date: February 2026. 
 	 
 
Contents 
Abstract	1 
1. Introduction	2 
1.1 Research Objectives	2 
1.2 Organization of the Paper	2 
2. Theoretical Foundations	4 
2.1 Knowledge Space Theory	4 
2.2 Inductive Item Tree Analysis Algorithm	4 
2.3 Noise Removal Network	5 
2.4 Semantic Classification of Items	5 
2.5 Semantic Web and Educational Ontologies	5 
3. System Architecture	6 
4. Applied Technologies	7 
5. Data Model	8 
6. Analytical Processing Flow	9 
6.1 Data Completion and Noise Removal	9 
6.2 Semantic Classification of Items	9 
6.3 Concept-Level Summarization	10 
6.4 Item Difficulty Analysis	10 
6.5 Prerequisite Relation Extraction	10 
6.6 Generation of the Knowledge State Space	10 
6.7 Ontology Visualization, Validation, and Generation	10 
7. Backend Server and REST API	11 
8. User Interface	13 
8.1 Data Entry	13 
8.2 Progress Tracking	13 
8.3 Results Overview	14 
8.4 Analysis History	17 
9. System Evaluation	18 
9.1 Structural Validation	18 
9.2 Semantic-Pedagogical Validation	18 
9.3 Operational Validation	19 
10. Discussion	20 
10.1 Advantages of the Proposed Solution	20 
10.2 Limitations	20 
10.3 Directions for Future Enhancement	20 
10.3.1 Pedagogical Extensibility	20 
10.3.2 Technical Robustness	20 
10.3.3 Interoperability	21 
11. Conclusion	22 
References	23 

 
Abstract 
In a modern educational environment, personalized learning presupposes the ability of the system to accurately model a student's knowledge and, based on that model, suggest an optimal order for acquiring new content. Knowledge space theory offers a mathematically rigorous framework for such modeling, but its application to empirical educational data remains challenging—especially when the input data are incomplete and the knowledge domains are semantically rich. 
This paper describes the architecture and implementation of a web platform that automates the generation of knowledge spaces from empirical student achievement data by applying an integrated analytical pipeline of nine consecutive stages. The system combines a denoising autoencoder network for filling incomplete data, transformer models for the semantic classification of educational items, and an inductive item tree analysis algorithm for extracting prerequisite relations. The resulting knowledge model is mapped to the ontological layer within the Contemporary Educational Technologies and Standards (SOTIS) project. 
The evaluation was conducted on a dataset with 692 students and 121 educational items organized into 7 concepts. The resulting knowledge space contains 44 valid states, and structural validation confirmed the model's full mathematical correctness.   
1. Introduction 
Personalized learning relies on the educational system's ability to determine for each student what they know, what they have not yet mastered, and the order in which they should acquire new knowledge. The knowledge space theory, formulated by Doignon and Falmagne (1985), offers a mathematical framework that makes this precisely possible: the domain of knowledge is modeled as a partially ordered set in which the prerequisite relation between educational items determines the set of attainable knowledge states for each student. This approach enables systematic inference about competencies and the automated creation of optimal learning paths. 
The practical application of this theory faces two key challenges. Manually defining prerequisite relations is time-consuming and prone to subjective errors, especially in domains with a large number of items. Educational data in real-world settings are rarely complete: missing values and measurement noise seriously compromise the quality of any analytical procedure. In the dataset analyzed in this paper, the proportion of missing responses is about 59%, making data imputation a necessary step before structural analysis. 
This paper presents a system that addresses both challenges in an integrative way. A denoising network provides robust completion of incomplete answer matrices; transformer models for semantic sentence representation enable the automatic grouping of items into coherent concepts; an inductive item tree analysis algorithm extracts the prerequisite structure from the prepared matrix without manual expert intervention. The system is positioned within the SOTIS project and generates a knowledge model that maps to an ontology layer for semantic interoperability. 
1.1 Research Objectives 
The research has four objectives: 
1.	describe the system architecture and the interdependencies of its subsystems; 
2.	document the methodological decisions of each of the nine phases of the analytical processing flow; 
3.	present a data model that coordinates asynchronous execution; 
4.	evaluate the system on an available dataset through structural, pedagogical, and operational validation. 
1.2 Organization of the Paper 
The paper is organized as follows. Section 2 provides the theoretical foundations of knowledge space theory, the inductive item tree analysis algorithm, denoising networks, and the Semantic Web. Section 3 describes the system architecture, Section 4 the applied technologies, and Section 5 the data model. Sections 6, 7, and 8 document the implementation of the three subsystems. Section 9 presents the evaluation results, Section 10 the discussion, and Section 11 concludes the paper. 
 	  
2. Theoretical Foundations 
2.1 Knowledge Space Theory 
The knowledge space theory was formulated by Doignon and Falmagne (1985) as a mathematical framework for modeling knowledge domains. Let Q be a finite set of educational items. A knowledge space (Q, K) is defined as the collection K   2^Q of reachable knowledge states, closed under intersections: 
  
Each state K   K represents the set of items that a student can correctly solve. The practical value of the model lies in defining a teaching path—a minimal sequence of steps that guides the student from an empty state to the goal—which enables efficient personalized instruction (Falmagne et al., 2013). 
2.2 Inductive Item Tree Analysis Algorithm 
The Inductive Item Tree Analysis (IITA) algorithm was developed by Dowling (1993) and Schrepp (2003) as a method for the automatic extraction of prerequisite relations from empirical response matrices. The central component of the algorithm is the matrix of contrary examples B: 
Bᵢⱼ  = 1 and rₛⱼ = 0}| 
where rₛᵢ denotes the correctness of student s's answer to item i. The value of Bᵢⱼ counts the counterexamples for the implication i ⇒ j — students who answered item i correctly, but not item j. The implication is accepted if the relative frequency of counterexamples falls below the threshold θ: 
Bᵢⱼ / |S| < θ 

2.3 Noise-Removal Network 
The denoising network, also known in the literature as a denoising autoencoder (DAE, Denoising Autoencoder), is described in the work of Vincent et al. (2008, 2010) as a neural network that is learned to reconstruct a clean input x from an artificially corrupted input x̃, generated by stochastically masking elements: 
x̃  ᵢ ~ Bernoulli(1 − p) 
The loss function is calculated exclusively on the observed values: 
L = (1/|Ω|) Σ Ω (xᵢ − x̂ᵢ)² 
where Ω denotes the set of indices for which the answer is available. This approach ensures that the network learns the structure of correlations between items and student achievements, and not just the raw distribution of the observed values. The reconstruction is binary thresholded at 0.5, resulting in a filled binary matrix suitable for further algorithmic processing. 
2.4 Semantic Classification of Items 
Effective application of knowledge space theory to domains with a large number of items requires their prior grouping into semantically coherent concepts. Reimers and Gurevych (2019) proposed an architecture that, using Siamese BERT networks, generates vector representations of sentences suitable for comparison with the cosine similarity measure. Hierarchical clustering is applied to the resulting vectors using the Ward method (Ward, 1963): a single parameter—the distance threshold—determines the number of clusters without manual tuning, which makes the system applicable to new domains without expert intervention. 
2.5 Semantic Web and Educational Ontologies 
The Contemporary Educational Technologies and Standards (SOTIS) project promotes the use of ontologies based on the Web Ontology Language (OWL) for the exchange of knowledge between heterogeneous educational systems (Horvat et al., 2012). OWL and the Resource Description Framework (RDF)—standards of the W3C consortium—enable the machine-readable description of educational content, prerequisite relationships, and learning paths, making them interoperable across different platforms. The system described in this paper generates a SOTIS-compatible ontology as the final result of the analytical processing flow, making the knowledge model semantically available outside the context of the platform itself. 
 	 
 
3. System Architecture 
The system consists of three logically separated components unified into a multi-container application based on a container orchestrator: a user interface, a back-end server, and an analytical workflow, along with a database and a middleware layer for message exchange. This architecture provides a clear separation of responsibilities—the time-consuming analytical processing occurs independently of user requests. 
 
  
        	 
Figure 1. High-level system architecture: user interface, back-end server, analytical workflow, database, and 
a message-broker layer. 
The primary processing flow is based on an asynchronous model. The user uploads the response matrix and optionally a document with item descriptions. The back-end server receives the request, creates the corresponding records in the database, and delegates the analytical task to the workflow. The user interface periodically checks the status and displays the progress in real time. Upon completion, all generated results are available for viewing and download. 
 	 
 
4. Applied Technologies 
The selection of the technology stack is based on criteria of production maturity, permissive licenses, and containerization capabilities. Tables 1, 2, and 3 provide an overview of the key technologies by subsystem. 
Technology 	Role in the system 
Python 3.11+ 	Base Runtime Environment 
FastAPI 0.109 	REST API framework with automatic documentation 
SQLAlchemy 2.0 	Object-relational mapping 
Celery 5.3 	Asynchronous task execution 
Redis 	Middleware for message passing 
PostgreSQL 15 	Relational database 
Pydantic 2.x 	Data validation and serialization 
Table 1. Backend server technologies. 
 
Library 	Purpose 
PyTorch 2.4 (CPU) 	Noise removal network 
sentence-transformers 	Vector representations of sentences 
scikit-learn 	Hierarchical clustering 
networkx 	Graph analysis and operations 
pandas / numpy 	Data manipulation and numerical processing 
rdflib 7.0 	Building and serialization of OWL ontology 
Table 2. Analytical processing flow libraries. 
 
Technology 	Role 
React 19 + TypeScript 5.9 	Component development with static typing 
Material-UI 5.14 	Pre-built user interface components 
React Flow 12.3 	Interactive graph visualization 
elkjs 0.11 	Layered graph node layout 
Nginx 	Static server and reverse proxy 
Table 3. User Interface Technologies. 
 
5. Data Model 
The relational schema comprises three interconnected entities that track the entire analysis lifecycle—from the initial file load to the storage of the output results. 
Entity 	Key attributes 	Purpose 
Loads 	id, file name, size, number of rows and columns, loading time 	Metadata about the input response matrix 
Task 	id, status (pending / in progress / completed / failed), progress (0–100%), message, parameters, time 	Lifecycle tracking for each analysis 
Result 	id, 	number 	of items/concepts/students/states/prerequisites, knowledge space (JSON) 	Quantitative indicators and preserved knowledge model 
Table 4. System relational schema. 
The Task entity tracks the analysis's status through four possible states. Progress and current message attributes are updated during execution and displayed in real-time within the user interface. Parameters are saved in a structured format, which guarantees the reproducibility of each analysis. 
 	 
 
6. Analytical Processing Flow 
The analytical processing flow is organized as a sequential series of nine consecutive phases, where each phase receives the structured output of the previous one and passes its result to the next. Figure 2 shows the entire flow with all phases, and all phases are described below with an emphasis on the rationale for the methodological decisions. 
 
  
Figure 2. The nine sequential phases of the analytical processing flow, from loading raw data to generating 
an OWL ontology. 
6.1 Data Imputation and Noise Removal 
The proportion of missing values in the input matrix is about 59%, which means that only about 41% of the individual-item level responses are known. Such data density directly precludes the reliable application of the algorithm to the raw data (see section 2.2). In response, the first phase trains a denoising autoencoder network on the available data, with the goal of learning the latent connections between educational items and student achievement. 
Why this approach? In contrast to simpler imputation methods—such as replacing with the arithmetic mean—the denoising network learns the data structure and fills in missing values consistently with each student's individual profile. During training, a portion of the observed values is intentionally hidden, forcing the network to reconstruct the hidden information. The reconstruction is binarized with a threshold of 0.5. 
The combined effect of imputation and subsequent compression to the concept level measurably improved data density: while at the individual-item level about 41% of responses are known, after semantic grouping and aggregation to concepts—and before final binarization—the proportion of known values increases to about 83.75% (unknown ~16.25%). This jump directly confirms that the combined approach significantly reduces the impact of data incompleteness on the quality of the input for the prerequisite-relation extraction algorithm. 
Repeatability is ensured by fixing the random seed to the value 42 and by exclusively using the CPU variant of the deep learning library, which guarantees identical results on all platforms. 
6.2 Semantic Classification of Items 
Each item is translated into a high-dimensional vector space by applying a pre-trained network for semantic sentence representations. The semantic similarity of items is measured by the cosine similarity between vectors, and hierarchical clustering using Ward's method merges them into coherent thematic clusters. A single parameter—the distance threshold— determines the number of groups without manual tuning. 
6.3 Concept-Level Summarization 
The binary response matrix is summarized from the level of individual items to the level of semantic concepts. A student is considered to have mastered a concept if they correctly answered more than half of the items for that concept. The result is a mastery matrix |S| × |C|, where S denotes the set of students and C the set of identified concepts. This step reduces the dimensionality of the problem and mitigates the variability of measurement errors. 
6.4 Item Difficulty Analysis 
The difficulty of each item is defined as the proportion of incorrect answers. Within each concept, items are ranked from the most difficult to the least difficult, yielding a pedagogical order suitable for the gradual introduction of complexity. 
6.5 Prerequisite Relation Extraction 
The application of the IITA algorithm is performed on the mastery matrix at the concept level. The algorithm accepts the implication i ⇒ j when the relative frequency of contrary examples falls below the threshold θ = 0.05. On the generated set of implications, a transitive reduction is applied, which removes edges derivable by composition of existing relations. Cycles are detected and removed through an iterative process, ensuring the structure of a directed acyclic graph. 
6.6 Generation of the Knowledge State Space 
Based on the prerequisite graph, a breadth-first search generates the set of all reachable knowledge states, starting from the empty state. State K is reached by adding concept c to state K' only if all prerequisites of concept c are already contained in K'. 
Combinatorial explosion is controlled through two mechanisms: states directly observed in the student data are always included, while states on the paths between them are included only if their cardinality is below an upper bound. The total number of states is limited by an upper bound that ensures practical applicability. 
6.7 Ontology Visualization, Validation, and Generation 
The generated prerequisite graph is visualized as a static diagram. Structural validation checks the graph's consistency: the presence of root concepts, the absence of cycles, the number of weakly connected components, and edge density. The final step generates an OWL ontology in RDF Turtle format, which contains concept instances, prerequisite relations, and item instances. 
7. Backend Server and REST API 
The backend server is organized as a monolithic REST application with automatically generated interactive documentation. Table 5 provides an overview of the API endpoints that cover the entire analysis lifecycle. 
Method 	Endpoint 	Description 
POST 	/run 	Start analysis (load data) 
GET 	/{id}/status 	Monitoring status and progress 
GET 	/{id}/statistics 	Quantitative indicators 
GET 	/{id}/knowledge-space 	Knowledge space in a structured form 
GET 	/{id}/goals 	List of learning goals (semantic query) 
GET 	/{id}/goal-path 	Recommended learning path to the goal 
GET 	/{id}/files 	List of generated results 
GET 	/{id}/download/{name} 	Download results 
GET 	/tasks 	History of all analyses 
DELETE 	/{id} 	Delete analysis and results 
Table 5. System REST API endpoints. 
The endpoints for managing learning goals and learning paths execute semantic queries over the generated OWL ontology, without introducing a separate triples store server. The analytics flow is executed as a background task that directly calls the analytics services, enabling transparent error forwarding and real-time progress updating. Table 6 shows the mapping of phases to percentage progress. 
Phase 	Description 	Progress 
1 	Data Preparation 	10% 
2 	Imputation and Noise Removal 	15–20% 
3 	Semantic classification 	25–35% 
4 	Concept-Level Summarization 	45–50% 
5 	Item Difficulty Analysis 	55–60% 
6 	Prerequisite Relation Extraction 	65–70% 
7 	State space generation 	75–80% 
8 	Visualization and validation 	85–88% 
9 	Ontology generation and storage 	90–100% 
Table 6. Mapping of phases to task progress percentage. 
 
 	  
8. User Interface 
The user interface is implemented as a web application with a linear flow through four functional phases: data entry, progress tracking, results overview, and analysis history. The identifier for the active analysis is stored locally in the browser, allowing the user to resume viewing after refreshing the page. 
8.1 Data Entry 
The user uploads the response matrix in CSV format and, optionally, a document with item descriptions. The interface provides immediate feedback on the format and dimensions of the uploaded data. 
 
Figure 3. Data input screen: fields for loading the response matrix and the item descriptions document. 
8.2 Progress Monitoring 
During the analysis, the interface displays a visual progress indicator with the description of the currently active phase and the completion percentage. Updates are performed by periodic queries to the backend server. 
 
 
Figure 4. Progress monitoring screen with a description of the active phase and the real-time completion 
percentage. 
8.3 Results Overview 
Upon completion of the analysis, the user is presented with a dashboard featuring statistical indicators, an interactive knowledge space graph, recommended learning paths, and a list of generated results. Figure 5 shows an overview of the key statistical indicators, and Figure 6 shows the interactive knowledge space graph. 
 
 
Figure 5. Statistical overview of the analysis results. 
 
Figure 6. Knowledge space graph with a visualization of prerequisite relationships between concepts. 
The knowledge space graph is visualized as an interactive diagram where nodes are arranged in layers according to their depth in the prerequisite hierarchy. The user can explore nodes, expand clusters, and search for concepts. Figure 7 shows the screen for planning the learning path, while Figure 8 shows the tab displaying all generated results with an option to download each file. 
 
Figure 7. Recommended learning path to the selected goal with concept order. 
 
Figure 8. List of generated results with a download option. 
8.4 Analysis History 
The interface provides an overview of all previously run analyses with statuses, run times, an option to reopen results, and a delete option. 
 
Figure 9. Overview of the analysis history with statuses and an option to review results. 
 	 
 
9. System Evaluation 
The system's evaluation was conducted on a dataset comprising 692 students and 121 educational items organized into 7 semantic concepts. The system's correctness and usability were verified at three levels: structural, semantic-pedagogical, and operational. 
9.1 Structural Validation 
Structural validation checks the mathematical correctness of the generated knowledge space and prerequisite graph. The key quantitative indicators are shown in Table 7. 
Metrics 	Value 
Number of students 	692 
Number of items 	121 
Data density (items, before processing) 	~41% 
Data density (concepts, after aggregation) 	~83.75% 
Number of concepts (final model) 	7 
Number of prerequisite relations 	5 
Number of knowledge states 	44 
Number of root concepts 	3 
Graph density 	0.1190 
Graph type 	Directed acyclic graph 
Number of weakly-connected components 	1 
Valid transitions (total) 	108 
Table 7. Quantitative indicators of structural validation. 
All 108 transitions between knowledge states add exactly one concept and respect all established prerequisite relations, which confirms the full mathematical consistency of the knowledge space. The prerequisite graph has the structure of a directed acyclic graph with one weakly connected component, which means that all concepts are reachable from at least one of the three root concepts. 
9.2 Semantic-Pedagogical Validation 
The semantic coverage of items is 99.17%: out of 121 items, 120 were successfully grouped into concepts, while one item remains unconnected due to differences in labeling between the item text and the descriptions in the attached document. This item does not compromise the structural validity of the model, but it indicates the need to standardize labeling in the input data. 
The pedagogical coherence of the prerequisite relations is confirmed by a qualitative analysis of the generated graph. The following examples illustrate the semantic meaningfulness of the extracted relations: 
–	Linear Equations and Graphs → Slope and Parallelism: Understanding slope and parallelism builds on the ability to read and form equations of lines and their graphical representations. 
–	Linear Equations and Graphs → Equations and Transformations: Working with equations of lines builds upon stable skills in algebraic rearranging and solving linear forms. 
–	Slope and Parallelism → Algebra and Terms: The formalization of slope and parallelism relationships requires reliable manipulation of terms and expressions at a more abstract algebraic level. 
9.3 Operational Validation 
Operational validation checks the stable operation of the system from loading input data to delivering all output results. The presence of all expected output files, the correctness of item ordering by difficulty within each concept, the correspondence of generated prerequisite relations to the reference set manually defined by the instructor, and the content of the ontology were verified. Comparative validation showed a high degree of correspondence of root concepts and satisfactory coverage of reference relations. 
 	 
 
10. Discussion 
10.1 Advantages of the Proposed Solution 
The three-tier architecture with asynchronous execution offers several measurable advantages. Workflows can be horizontally scaled independently of the back-end server, and the middleware message-passing layer enables distributed execution without changes to the application code. The modular organization of the subsystems allows for the independent testing and replacement of each component. Guaranteed reproducibility of results is particularly important for scientific research and pedagogical evaluation. The ontological representation of knowledge in the SOTIS namespace opens up the possibility of semantic queries and integration with systems that support Semantic Web standards. 
10.2 Limitations 
Three limitations relevant to applications in new domains have been identified. The detection of items in the input matrix relies on a column-naming convention specific to the structure of the analyzed curriculum, which requires adaptation when transitioning to another domain. Relational schema change management is only partially implemented: versioned migration scripts are not implemented, which prevents safe updating in a production environment. Finally, knowledge state space generation has exponential theoretical complexity, and the upper bounds established are sufficient for the analyzed set, but may cause incomplete exploration in domains with denser prerequisite graphs. 
10.3 Directions for Future Improvement 
10.3.1 Pedagogical Extensibility 
The most immediate next step in the system's development is the introduction of adaptive computational knowledge assessment. Based on the currently inferred state of the student's knowledge, such a module would select the next task that provides the maximum diagnostic information—directly transforming the platform from an analytical tool into an adaptive tutoring system. A promising direction is also support for graded responses—where the degree of correctness is recorded, not just true/false—which would allow for a finer granularity of the knowledge state and application in domains with more complex scoring systems. 
10.3.2 Technical Robustness 
Introducing versioned migration scripts for the relational schema is a necessary step before production deployment. The empirically established 20% threshold for missing values has not yet been formally quantified across different domains; a systematic experimental study with controlled levels of data incompleteness would provide more reliable guidance for parameter tuning in new application contexts.  

For domains with dense prerequisite graphs, research into approximate methods for state-space generation could significantly improve scalability. 
10.3.3 Interoperability 
Support for standardized educational data exchange formats—primarily IMS QTI for importing assignments and xAPI for tracking progress—would enable integration with learning management platforms such as Moodle and Canvas. The generated ontology provides the semantic foundation for such integrability; the necessary next step is its mapping to standardized metadata models such as IEEE LOM or the schema.org vocabulary. 
 	 
 
11. Conclusion 
This paper describes the design, implementation, and evaluation of a platform for the automated generation of knowledge spaces from empirical student achievement data, based on knowledge space theory. The proposed system integrates three complementary methods into a single analytical pipeline: a denoising network for robustly filling incomplete response matrices, semantic item classification via transformer models, and an inductive item tree analysis algorithm for extracting prerequisite relations without manual expert intervention. 
An evaluation conducted on a dataset with 692 students, 121 items, and 7 semantic concepts showed that the system generates a mathematically consistent knowledge space of 44 states, with 5 prerequisite relations and full structural correctness: all 108 transitions respect prerequisite relations and add exactly one concept. The semantic coverage of items is 99.17%, and the pedagogical coherence of the relations is confirmed by a qualitative analysis aligned with the reference curriculum. 
The system is positioned within the SOTIS project and generates an OWL ontology compatible with Semantic Web standards. Identified limitations—a column-naming convention specific to the analyzed domain and the absence of versioned migration scripts— are transparently documented as starting points for future development. Planned extensions—adaptive knowledge assessment, support for graded responses, and integration with standardized educational data formats—define clear avenues for the evolutionary development from a research platform to an operational component of modern educational technologies. 
 	 
 
References 
Doignon, J. P., & Falmagne, J. C. (1985). Spaces for the assessment of knowledge. International Journal of Man-Machine Studies, 23(2), 175–196. https://doi.org/10.1016/S0020-7373(85)80031-6 
Dowling, C. E. (1993). On the irredundant generation of knowledge spaces. Journal of Mathematical Psychology, 37(1), 49–62. https://doi.org/10.1006/jmps.1993.1004 
Falmagne, J. C., Albert, D., Doble, C., Eppstein, D., and Hu, X. (2013). Knowledge spaces: Applications in education. Springer. 
Horvat, D., Dobša, J., & Divjak, B. (2012). Application of knowledge space theory in an e-learning system. Proceedings of the Central European Conference on Information and Intelligent Systems, 11–18. 
Reimers, N., and Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese 
BERT-networks. Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing, 3982–3992. https://doi.org/10.18653/v1/D19-4006 
Schrepp, M. (2003). A method for the analysis of hierarchical dependencies between items of a questionnaire. Methods of Psychological Research Online, 19, 43–79. 
Vincent, P., Larochelle, H., Bengio, Y., and Manzagol, P. A. (2008). Extracting and composing robust features with denoising autoencoders. Proceedings of the 25th 
International 	Conference 	on 	Machine 	Learning, 	1096–1103. https://doi.org/10.1145/1390156.1390294 
Vincent, P., Larochelle, H., Lajoie, I., Bengio, Y., and Manzagol, P. A. (2010). Stacked denoising autoencoders: Learning useful representations in a deep network with a local denoising criterion. Journal of Machine Learning Research, 11, 3371–3408. 
Ward, J. H. (1963). Hierarchical grouping to optimize an objective function. Journal of the 
	American 	Statistical 	Association, 	58(301), 	236–244. 
https://doi.org/10.1080/01621459.1963.10500845 
 
Note: All quantitative results presented in Section 9 were obtained by applying the described system to a dataset available within the analyzed educational context. The images in Section 8 show the actual user interface of the implemented platform. 
