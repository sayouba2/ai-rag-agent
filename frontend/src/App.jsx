import { useState } from "react";
import { askQuestion, uploadFiles } from "./api";

export default function App() {
    const [question, setQuestion] = useState("");
    const [answer, setAnswer] = useState("");
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [uploadMessage, setUploadMessage] = useState("");

    const handleUpload = async () => {
        if (!files.length) return;

        try {
            setLoading(true);
            setUploadMessage("");
            const result = await uploadFiles(files);
            setUploadMessage(
                `${result.message} Chunks indexed: ${result.files_indexed}`
            );
        } catch (error) {
            setUploadMessage("Upload failed.");
        } finally {
            setLoading(false);
        }
    };

    const handleAsk = async () => {
        if (!question.trim()) return;

        try {
            setLoading(true);
            setAnswer("");
            const result = await askQuestion(question);
            setAnswer(result.answer);
        } catch (error) {
            setAnswer("Failed to get response.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <h1>AI RAG Agent</h1>

            <section style={styles.section}>
                <h2>1. Upload documents</h2>
                <input
                    type="file"
                    multiple
                    accept=".pdf,.txt"
                    onChange={(e) => setFiles(Array.from(e.target.files))}
                />
                <button onClick={handleUpload} disabled={loading}>
                    {loading ? "Uploading..." : "Upload and Index"}
                </button>
                {uploadMessage && <p>{uploadMessage}</p>}
            </section>

            <section style={styles.section}>
                <h2>2. Ask a question</h2>
                <textarea
                    rows="5"
                    placeholder="Ask something about your uploaded documents..."
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    style={styles.textarea}
                />
                <button onClick={handleAsk} disabled={loading}>
                    {loading ? "Thinking..." : "Ask"}
                </button>
            </section>

            <section style={styles.section}>
                <h2>Answer</h2>
                <div style={styles.answerBox}>{answer || "No answer yet."}</div>
            </section>
        </div>
    );
}

const styles = {
    container: {
        maxWidth: "900px",
        margin: "40px auto",
        fontFamily: "Arial, sans-serif",
        padding: "20px",
    },
    section: {
        marginBottom: "30px",
        padding: "20px",
        border: "1px solid #ddd",
        borderRadius: "10px",
    },
    textarea: {
        width: "100%",
        marginBottom: "10px",
        padding: "10px",
        fontSize: "16px",
    },
    answerBox: {
        minHeight: "120px",
        whiteSpace: "pre-wrap",
        background: "#f8f8f8",
        padding: "15px",
        borderRadius: "8px",
        border: "1px solid #ddd",
    },
};