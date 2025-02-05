// server.js
import express from 'express';
import { Initiator } from './utils/pythonScriptRunner.js';
import { MongoClient, ObjectId } from 'mongodb';
import { getContext, openai } from './utils/openAi.js';
const app = express();
app.use(express.json());

app.post('/process-url', async (req, res) => {
    try {
        const { url, source, institutionName, businessName, systemPrompt, tools } = req.body;
        let UserPrompt = "For this query, the system has retrieved the following relevant information from ${businessName}’s database:  \n ${contexts}  \n Using this institutional data, generate a clear, precise, and tailored response to the following user inquiry: \n ${userMessage}  \n If the retrieved data does not fully cover the query, acknowledge the limitation while still providing the most relevant response possible."
        if (!url || !source) return res.status(400).json({ error: 'Missing url or source' });
        const client = await MongoClient.connect(process.env.MONGO_URL);
        await Initiator(url, source, institutionName);
        const mainDoc = await client.db("Demonstrations").collection("Admin").insertOne({ sitemap: url, businessName, institutionName, systemPrompt, UserPrompt, tools });
        return res.json({
            success: true, 
            data: mainDoc
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});
app.get("/client/:clientId", async () => {
    try {
        const client = await MongoClient.connect(process.env.MONGO_URL);
        let clientDetails = await client.db("Demonstrations").collection("Admin").findOne({ _id: new ObjectId(req.params.clientId) }, { projection: { businessName: 1 } });
        res.status(200).json({ success: true, message: "Client info", data: clientDetails })
    } catch (error) {
        console.log(error);
        res.status(500).json({ error: error.message });
    }
})
app.post('/chat-bot', async (req, res) => {
    try {
        const { userMessage, prevMessages = [], clientId, streamOption = false } = req.body;
        const client = await MongoClient.connect(process.env.MONGO_URL);
        let { institutionName, businessName, systemPrompt, UserPrompt, tools } = await client.db("Demonstrations").collection("Admin").findOne({ _id: new ObjectId(clientId) });
        const contexts = await getContext(institutionName, userMessage)
        if (contexts == "") console.log("Empty context received")
        if (!streamOption) {
            const response = await openai.chat.completions.create({
                model: "gpt-4o-mini",
                messages: [
                    { "role": "system", "content": systemPrompt, },
                    ...prevMessages,
                    {
                        role: "user",
                        content: UserPrompt.replace("${contexts}", contexts).replace("${userMessage}", userMessage).replace("${businessName}", businessName)
                    }],
                tools: tools.length > 1 ? tools : null,
                store: tools.length > 1 ? true : null,
                tool_choice: tools.length > 1 ? "auto" : null,
            })
            return res.status(200).send({ success: true, data: response.choices[0].message.content })
        }
        const stream = await openai.chat.completions.create({
            model: "gpt-4o-mini",
            messages: [
                { "role": "system", "content": systemPrompt, },
                ...prevMessages,
                {
                    role: "user",
                    content: UserPrompt.replace("${contexts}", contexts).replace("${userMessage}", userMessage)
                }],
            stream: true,
            tools: tools.length > 1 ? tools : null,
            store: tools.length > 1 ? true : null,
            tool_choice: tools.length > 1 ? "auto" : null,
        });
        let finalToolCalls = [];
        res.setHeader('Content-Type', 'text/plain');
        res.setHeader('Transfer-Encoding', 'chunked');
        for await (const chunk of stream) {
            const toolCalls = chunk.choices[0].delta.tool_calls || [];
            for (const toolCall of toolCalls) {
                const { index } = toolCall;
                if (!finalToolCalls[index]) finalToolCalls[index] = toolCall;
                finalToolCalls[index].function.arguments += toolCall.function.arguments;
            }
            if (chunk.choices[0]?.delta?.content !== null && chunk.choices[0]?.delta?.content !== undefined) res.write(JSON.stringify({ chunk: chunk.choices[0]?.delta?.content, toolResponse: [] }));
        }
        const functionCalls = []
        finalToolCalls.forEach(ele => {
            let parameters = JSON.parse(ele.function.arguments); // Parse the arguments string
            let functionName = ele.function.name; // Get the function name
            const result = toolFunctions[functionName](parameters)
            functionCalls.push(result)
        });
        console.log("chunking done, sending all at once");
        res.end(JSON.stringify({
            chunk: "",
            toolResponse: functionCalls
        }))
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: error.message });
    }
});
const PORT = process.env.PORT;
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
