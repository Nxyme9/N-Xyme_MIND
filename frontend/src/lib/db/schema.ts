const DB_NAME = 'nxyme-mind-undo';
const DB_VERSION = 1;

export interface Snapshot {
  id?: number;
  timestamp: number;
  state: string;
  description: string;
}

export interface Action {
  id?: number;
  timestamp: number;
  type: 'create' | 'update' | 'delete';
  entityType: string;
  entityId: string;
  previousState: string | null;
  newState: string | null;
  source: string;
}

export interface UndoEntry {
  id?: number;
  timestamp: number;
  actionIds: number[];
  description: string;
  undone: boolean;
}

const STORES = {
  snapshots: { keyPath: 'id', autoIncrement: true, indexes: [
    { name: 'timestamp', keyPath: 'timestamp' },
  ]},
  actions: { keyPath: 'id', autoIncrement: true, indexes: [
    { name: 'timestamp', keyPath: 'timestamp' },
    { name: 'type', keyPath: 'type' },
    { name: 'entityType', keyPath: 'entityType' },
    { name: 'entityId', keyPath: 'entityId' },
  ]},
  undos: { keyPath: 'id', autoIncrement: true, indexes: [
    { name: 'timestamp', keyPath: 'timestamp' },
    { name: 'undone', keyPath: 'undone' },
  ]},
};

let dbInstance: IDBDatabase | null = null;

export async function openDatabase(): Promise<IDBDatabase> {
  if (dbInstance) return dbInstance;

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      dbInstance = request.result;
      resolve(dbInstance);
    };

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      if (!db.objectStoreNames.contains('snapshots')) {
        const snapshotStore = db.createObjectStore('snapshots', { keyPath: 'id', autoIncrement: true });
        snapshotStore.createIndex('timestamp', 'timestamp', { unique: false });
      }

      if (!db.objectStoreNames.contains('actions')) {
        const actionStore = db.createObjectStore('actions', { keyPath: 'id', autoIncrement: true });
        actionStore.createIndex('timestamp', 'timestamp', { unique: false });
        actionStore.createIndex('type', 'type', { unique: false });
        actionStore.createIndex('entityType', 'entityType', { unique: false });
        actionStore.createIndex('entityId', 'entityId', { unique: false });
      }

      if (!db.objectStoreNames.contains('undos')) {
        const undoStore = db.createObjectStore('undos', { keyPath: 'id', autoIncrement: true });
        undoStore.createIndex('timestamp', 'timestamp', { unique: false });
        undoStore.createIndex('undone', 'undone', { unique: false });
      }
    };
  });
}

export async function addSnapshot(snapshot: Omit<Snapshot, 'id'>): Promise<number> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('snapshots', 'readwrite');
    const store = tx.objectStore('snapshots');
    const request = store.add(snapshot);
    request.onsuccess = () => resolve(request.result as number);
    request.onerror = () => reject(request.error);
  });
}

export async function getSnapshot(id: number): Promise<Snapshot | undefined> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('snapshots', 'readonly');
    const store = tx.objectStore('snapshots');
    const request = store.get(id);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function getLatestSnapshot(): Promise<Snapshot | undefined> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('snapshots', 'readonly');
    const store = tx.objectStore('snapshots');
    const request = store.openCursor(null, 'prev');
    request.onsuccess = () => resolve(request.result?.value);
    request.onerror = () => reject(request.error);
  });
}

export async function addAction(action: Omit<Action, 'id'>): Promise<number> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('actions', 'readwrite');
    const store = tx.objectStore('actions');
    const request = store.add(action);
    request.onsuccess = () => resolve(request.result as number);
    request.onerror = () => reject(request.error);
  });
}

export async function getActionsByEntity(entityType: string, entityId: string): Promise<Action[]> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('actions', 'readonly');
    const store = tx.objectStore('actions');
    const index = store.index('entityType');
    const request = index.getAll(IDBKeyRange.only(entityType));
    request.onsuccess = () => {
      const results = request.result.filter((a: Action) => a.entityId === entityId);
      resolve(results);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function addUndo(undo: Omit<UndoEntry, 'id'>): Promise<number> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('undos', 'readwrite');
    const store = tx.objectStore('undos');
    const request = store.add(undo);
    request.onsuccess = () => resolve(request.result as number);
    request.onerror = () => reject(request.error);
  });
}

export async function getPendingUndos(): Promise<UndoEntry[]> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('undos', 'readonly');
    const store = tx.objectStore('undos');
    const index = store.index('undone');
    const request = index.getAll(IDBKeyRange.only(false));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function markUndoAsDone(id: number): Promise<void> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('undos', 'readwrite');
    const store = tx.objectStore('undos');
    const getRequest = store.get(id);
    getRequest.onsuccess = () => {
      const undo = getRequest.result;
      if (undo) {
        undo.undone = true;
        store.put(undo);
      }
      resolve();
    };
    getRequest.onerror = () => reject(getRequest.error);
  });
}

export async function clearOldSnapshots(maxAgeMs: number = 7 * 24 * 60 * 60 * 1000): Promise<number> {
  const db = await openDatabase();
  const cutoff = Date.now() - maxAgeMs;
  let deleted = 0;

  return new Promise((resolve, reject) => {
    const tx = db.transaction('snapshots', 'readwrite');
    const store = tx.objectStore('snapshots');
    const request = store.openCursor();
    
    request.onsuccess = () => {
      const cursor = request.result;
      if (cursor) {
        if (cursor.value.timestamp < cutoff) {
          cursor.delete();
          deleted++;
        }
        cursor.continue();
      }
    };
    tx.oncomplete = () => resolve(deleted);
    tx.onerror = () => reject(tx.error);
  });
}