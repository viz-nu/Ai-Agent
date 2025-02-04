import OpenAI from "openai";
import { MongoClient } from "mongodb"
export const openai = new OpenAI({ apiKey: process.env.OPEN_API_KEY });
export const EmbeddingFunct = async (text) => {
    try {
        const { data } = await openai.embeddings.create({
            model: "text-embedding-3-small",
            input: text,
            encoding_format: "float",
        });
        return data[0].embedding;
    } catch (error) {
        console.log(error);
        return null;
    }
}
export const getContext = async (institutionName, text) => {
    const dbName = 'Demonstrations';
    const client = await MongoClient.connect(process.env.MONGO_URL);
    const db = client.db(dbName);
    try {
        let context = await db.collection('Data').aggregate([
            {
                "$vectorSearch": {
                    "exact": false,
                    "filter": {"metadata.institutionName":institutionName},
                    "index": "Data",
                    "path": "embeddingVector",
                    "queryVector": await EmbeddingFunct(text),
                    "numCandidates": 100,
                    "limit": 3
                }
            },
            {
                $project: {
                    content: 1,
                    score: { $meta: 'vectorSearchScore' }
                }
            }
        ]).toArray()
        client.close();
        return context.reduce((acc, ele) => acc += `\n${ele.content}\n`, "");
    } catch (error) {
        client.close();
        console.log(error);
        return null;
    }
}