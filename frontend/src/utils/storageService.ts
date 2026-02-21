/**
 * Storage Service
 * Manage persistent storage for Knowledge Space data in localStorage.
 */

export interface StorageData {
  knowledgeSpace: Record<string, string[]> | null;
  implications: Array<{ source: string; target: string }> | null;
  statistics: Record<string, unknown> | null;
  currentTaskId: string | null;
  lastUpdated: string;
}

const STORAGE_PREFIX = 'ksb_';
const KNOWLEDGE_SPACE_KEY = `${STORAGE_PREFIX}knowledge_space`;
const IMPLICATIONS_KEY = `${STORAGE_PREFIX}implications`;
const STATISTICS_KEY = `${STORAGE_PREFIX}statistics`;
const TASK_ID_KEY = `${STORAGE_PREFIX}task_id`;

class StorageService {
  /**
   * Save the knowledge space graph
   */
  saveKnowledgeSpace(data: Record<string, string[]>): void {
    try {
      localStorage.setItem(KNOWLEDGE_SPACE_KEY, JSON.stringify(data));
      this.updateTimestamp();
    } catch (error) {
      console.error('Error saving knowledge space:', error);
    }
  }

  /**
   * Load the knowledge space graph
   */
  loadKnowledgeSpace(): Record<string, string[]> | null {
    try {
      const data = localStorage.getItem(KNOWLEDGE_SPACE_KEY);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Error loading knowledge space:', error);
      return null;
    }
  }

  /**
   * Save implications
   */
  saveImplications(data: Array<{ source: string; target: string }>): void {
    try {
      localStorage.setItem(IMPLICATIONS_KEY, JSON.stringify(data));
      this.updateTimestamp();
    } catch (error) {
      console.error('Error saving implications:', error);
    }
  }

  /**
   * Load implications
   */
  loadImplications(): Array<{ source: string; target: string }> | null {
    try {
      const data = localStorage.getItem(IMPLICATIONS_KEY);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Error loading implications:', error);
      return null;
    }
  }

  /**
   * Save statistics
   */
  saveStatistics(data: Record<string, unknown> | any): void {
    try {
      localStorage.setItem(STATISTICS_KEY, JSON.stringify(data));
      this.updateTimestamp();
    } catch (error) {
      console.error('Error saving statistics:', error);
    }
  }

  /**
   * Load statistics
   */
  loadStatistics(): Record<string, unknown> | any | null {
    try {
      const data = localStorage.getItem(STATISTICS_KEY);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Error loading statistics:', error);
      return null;
    }
  }

  /**
   * Save current task ID
   */
  saveCurrentTaskId(taskId: string): void {
    try {
      localStorage.setItem(TASK_ID_KEY, taskId);
      this.updateTimestamp();
    } catch (error) {
      console.error('Error saving task ID:', error);
    }
  }

  /**
   * Load current task ID
   */
  loadCurrentTaskId(): string | null {
    try {
      return localStorage.getItem(TASK_ID_KEY);
    } catch (error) {
      console.error('Error loading task ID:', error);
      return null;
    }
  }

  /**
   * Clear all stored data
   */
  clearAll(): void {
    try {
      localStorage.removeItem(KNOWLEDGE_SPACE_KEY);
      localStorage.removeItem(IMPLICATIONS_KEY);
      localStorage.removeItem(STATISTICS_KEY);
      localStorage.removeItem(TASK_ID_KEY);
    } catch (error) {
      console.error('Error clearing storage:', error);
    }
  }

  /**
   * Check if any data is available
   */
  hasData(): boolean {
    return !!(
      localStorage.getItem(KNOWLEDGE_SPACE_KEY) ||
      localStorage.getItem(IMPLICATIONS_KEY)
    );
  }

  /**
   * Load all available data
   */
  loadAll(): StorageData {
    return {
      knowledgeSpace: this.loadKnowledgeSpace(),
      implications: this.loadImplications(),
      statistics: this.loadStatistics(),
      currentTaskId: this.loadCurrentTaskId(),
      lastUpdated: localStorage.getItem(`${STORAGE_PREFIX}timestamp`) || '',
    };
  }

  /**
   * Save multiple data entries at once
   */
  saveAll(data: Partial<StorageData>): void {
    if (data.knowledgeSpace) this.saveKnowledgeSpace(data.knowledgeSpace);
    if (data.implications) this.saveImplications(data.implications);
    if (data.statistics) this.saveStatistics(data.statistics);
    if (data.currentTaskId) this.saveCurrentTaskId(data.currentTaskId);
  }

  /**
   * Estimate total size of stored data in characters
   */
  estimateSize(): number {
    let size = 0;
    const keys = [KNOWLEDGE_SPACE_KEY, IMPLICATIONS_KEY, STATISTICS_KEY, TASK_ID_KEY];
    keys.forEach((key) => {
      const item = localStorage.getItem(key);
      if (item) {
        size += item.length;
      }
    });
    return size;
  }

  private updateTimestamp(): void {
    localStorage.setItem(`${STORAGE_PREFIX}timestamp`, new Date().toISOString());
  }
}

export const storageService = new StorageService();
