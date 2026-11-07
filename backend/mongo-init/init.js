db = db.getSiblingDB('health_rag');

db.createCollection('documents');

db.documents.createIndex({ "url": 1 }, { unique: true });
db.documents.createIndex({ "metadata.source": 1 });
db.documents.createIndex({ "metadata.ingested_at": 1 });
