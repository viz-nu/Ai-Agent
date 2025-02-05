import { spawn } from 'child_process';
import { MongoClient, ObjectId } from "mongodb";
import { EmbeddingFunct } from './openAi.js';
const installPythonPackages = async () => {
    return new Promise((resolve, reject) => {
        const pipProcess = spawn('pip', ['install', '-r', 'requirements.txt']);
        // pipProcess.stdout.on('data', (data) => console.log(`pip: ${data.toString()}`));
        // pipProcess.stderr.on('data', (data) => console.error(`pip error: ${data.toString()}`));
        pipProcess.on('close', (code) => { code === 0 ? resolve("All Python dependencies installed") : reject(new Error('Failed to install Python dependencies.')); });
    });
};
const runPythonScript = async ({ url, source, databaseConnectionStr, institutionName }) => {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', ['script.py', url, source, databaseConnectionStr, "Demonstrations", "Data", institutionName]);
        let result = '';
        let error = '';
        pythonProcess.stdout.on('data', (data) => console.log(data.toString()));
        pythonProcess.stderr.on('data', (data) => console.log(data.toString()));
        pythonProcess.on('close', (code) => { (code === 0) ? resolve(result.trim()) : reject(new Error(`Python script error: ${error}`)) });
    });
};
const insertEmbeddings = async () => {
    const url = process.env.MONGO_URL;
    const client = await MongoClient.connect(url);
    try {
        const db = client.db("Demonstrations");
        const collection = db.collection("Data");
        const totalDocs = await collection.countDocuments({ embeddingVector: { $exists: false } });
        if (totalDocs === 0) {
            console.log("No documents need processing.");
            return null;
        }
        const numParts = 10;
        const batchSize = Math.ceil(totalDocs / numParts); // 10 parts
        console.log(`Total Documents: ${totalDocs}`);
        console.log(`Processing in ${numParts} parts with batch size: ${batchSize}`);
        let processedCount = 0;
        for (let i = 0; i < numParts; i++) {
            const docs = await collection.find(
                { embeddingVector: { $exists: false } },
                { projection: { content: 1 } }
            )
                .limit(batchSize) // Fetch only the batch size
                .toArray();
            if (docs.length === 0) break; // Stop when no more docs
            // Generate embeddings in parallel
            const updates = await Promise.all(
                docs.map(async (doc) => ({
                    updateOne: {
                        filter: { _id: doc._id },
                        update: { $set: { embeddingVector: await EmbeddingFunct(doc.content) } }
                    }
                }))
            );
            // Perform bulk update
            if (updates.length > 0) {
                await collection.bulkWrite(updates);
                processedCount += docs.length;
                console.log(`Processed ${processedCount} / ${totalDocs} documents.`);
            }
        }

        return { status: "success", message: "Embeddings Completed" };

    }
    catch (error) {
        console.log(error);
    }
}
async function NewSearchIndex() {
    const client = new MongoClient(process.env.MONGO_URL);
    try {
        const database = client.db("Demonstrations");
        const collection = database.collection("Data");
        // define your Atlas Search index
        const index = {
            name: "Data",
            type: "vectorSearch",
            definition: {
                "fields": [
                    {
                        "type": "vector",
                        "numDimensions": 1536,
                        "path": "embeddingVector",
                        "similarity": "cosine",
                        "quantization": "scalar"
                    },
                    {
                        "type": "filter",
                        "path": "metadata.institutionName",
                    }
                ]
            }
        }
        let result = await collection.listSearchIndexes().toArray();
        let indexExists = result.some(idx => idx.name === "Data");
        if (!indexExists) {
            console.log("Creating new search index...");
            result = await collection.createSearchIndex(index);
            console.log(`New search index named '${result}' is building.`);

            // Wait for index to become queryable
            console.log("Polling to check if the index is ready. This may take up to a minute.");
            let isQueryable = false;
            while (!isQueryable) {
                const indexes = await collection.listSearchIndexes().toArray();
                const dataIndex = indexes.find(idx => idx.name === "Data");
                if (dataIndex?.queryable) {
                    console.log(`Index '${result}' is ready for querying.`);
                    isQueryable = true;
                } else {
                    await new Promise(resolve => setTimeout(resolve, 5000));
                }
            }
        } else {
            console.log("Search index already exists, updating...");
            await collection.updateSearchIndex("Data", index);
        }


    } finally {
        await client.close();
        return { status: "success", message: "Vector index created" };
    }
}
export const Initiator = async (url, source, institutionName) => {
    try {
        await installPythonPackages(); // Ensure dependencies are installed
        let databaseConnectionStr = process.env.MONGO_URL
        await runPythonScript({ url, source, databaseConnectionStr, institutionName });
        await insertEmbeddings()
        await NewSearchIndex()
        return { success: true, message: "initiation successFull" }
    } catch (error) {
        console.error(`Error: ${error.message}`);
    }
};
