import { useEffect, useRef, useState } from "react";
import { askQuestionStream, clearHistory, uploadFiles } from "./api";
import "./App.css";

export default function App() {
    const [messages, setMessages] = useState([]);
    const [question, setQuestion] = useState("");
    const [files, setFiles] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState(null); // {type, text}
    const [streamingAnswer, setStreamingAnswer] = useState("");
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, streamingAnswer]);

    // -----------------------------------------------------------------------
    // Upload
    // -----------------------------------------------------------------------

    const handleUpload = async () => {
        if (!files.length) return;
        setLoading(true);
        setUploadStatus(null);
        try {
            const result = await uploadFiles(files);
            setUploadStatus({
                type: "success",
                text: `${result.message} ${result.chunks_added} chunks ajoutés${result.files_skipped ? `, ${result.files_skipped} fichier(s) déjà indexé(s) ignoré(s)` : ""}.`,
            });
            setFiles([]);
        } catch (err) {
            setUploadStatus({ type: "error", text: err.message || "Upload échoué." });
        } finally {
            setLoading(false);
        }
    };

    // -----------------------------------------------------------------------
    // Ask (streaming)
    // -----------------------------------------------------------------------

    const handleAsk = async () => {
        if (!question.trim() || loading) return;

        const userText = question.trim();
        setMessages((prev) => [...prev, { role: "human", content: userText }]);
        setQuestion("");
        setLoading(true);
        setStreamingAnswer("");

        let fullAnswer = "";
        let collectedSources = [];

        try {
            await askQuestionStream(
                userText,
                sessionId,
                (token) => {
                    fullAnswer += token;
                    setStreamingAnswer((prev) => prev + token);
                },
                (sources) => {
                    collectedSources = sources;
                },
                (newSessionId) => {
                    setSessionId(newSessionId);
                    setMessages((prev) => [
                        ...prev,
                        { role: "ai", content: fullAnswer, sources: collectedSources },
                    ]);
                    setStreamingAnswer("");
                    setLoading(false);
                },
            );
        } catch {
            setMessages((prev) => [
                ...prev,
                { role: "ai", content: "Impossible d'obtenir une réponse.", sources: [] },
            ]);
            setStreamingAnswer("");
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleAsk();
        }
    };

    const handleClear = async () => {
        if (sessionId) await clearHistory(sessionId);
        setSessionId(null);
        setMessages([]);
    };

    // -----------------------------------------------------------------------
    // Render
    // -----------------------------------------------------------------------

    return (
        <div style={styles.container}>
            <h1 style={styles.title}>AI RAG Agent</h1>

            {/* ---- Upload ---- */}
            <section style={styles.uploadSection}>
                <h2 style={styles.sectionTitle}>Documents</h2>
                <p style={styles.hint}>
                    Formats supportés : PDF, TXT, DOCX, Markdown, CSV — max&nbsp;50&nbsp;Mo par fichier.
                </p>
                <div style={styles.uploadRow}>
                    <label style={styles.fileLabel}>
                        {files.length
                            ? `${files.length} fichier(s) sélectionné(s)`
                            : "Choisir des fichiers…"}
                        <input
                            type="file"
                            multiple
                            accept=".pdf,.txt,.docx,.md,.csv"
                            style={{ display: "none" }}
                            onChange={(e) => setFiles(Array.from(e.target.files))}
                        />
                    </label>
                    <button
                        onClick={handleUpload}
                        disabled={loading || !files.length}
                        style={{ ...styles.btn, ...(loading || !files.length ? styles.btnDisabled : {}) }}
                    >
                        {loading ? "Traitement…" : "Uploader & Indexer"}
                    </button>
                </div>
                {uploadStatus && (
                    <p style={uploadStatus.type === "success" ? styles.successMsg : styles.errorMsg}>
                        {uploadStatus.text}
                    </p>
                )}
            </section>

            {/* ---- Chat ---- */}
            <section style={styles.chatSection}>
                <div style={styles.chatHeader}>
                    <h2 style={styles.sectionTitle}>Chat</h2>
                    {messages.length > 0 && (
                        <button onClick={handleClear} style={styles.clearBtn}>
                            Nouvelle conversation
                        </button>
                    )}
                </div>

                <div style={styles.messageList}>
                    {messages.length === 0 && !streamingAnswer && (
                        <p style={styles.emptyState}>
                            Uploadez des documents puis posez vos questions.
                        </p>
                    )}

                    {messages.map((msg, i) => (
                        <div
                            key={i}
                            style={msg.role === "human" ? styles.humanBubble : styles.aiBubble}
                        >
                            <p style={styles.msgContent}>{msg.content}</p>

                            {msg.sources?.length > 0 && (
                                <details style={styles.sourcesDetails}>
                                    <summary style={styles.sourcesSummary}>
                                        {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
                                    </summary>
                                    <div style={styles.sourcesList}>
                                        {msg.sources.map((s, j) => (
                                            <div key={j} style={styles.sourceItem}>
                                                <span style={styles.sourceFilename}>{s.filename}</span>
                                                {s.page != null && (
                                                    <span style={styles.sourcePage}>
                                                        &nbsp;— page {s.page + 1}
                                                    </span>
                                                )}
                                                <p style={styles.sourceExcerpt}>{s.excerpt}</p>
                                            </div>
                                        ))}
                                    </div>
                                </details>
                            )}
                        </div>
                    ))}

                    {streamingAnswer && (
                        <div style={styles.aiBubble}>
                            <p style={styles.msgContent}>
                                {streamingAnswer}
                                <span className="cursor">▍</span>
                            </p>
                        </div>
                    )}

                    <div ref={bottomRef} />
                </div>

                {/* Input */}
                <div style={styles.inputRow}>
                    <textarea
                        rows="3"
                        placeholder="Posez une question… (Entrée pour envoyer, Maj+Entrée pour sauter une ligne)"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={handleKeyDown}
                        disabled={loading}
                        style={styles.textarea}
                    />
                    <button
                        onClick={handleAsk}
                        disabled={loading || !question.trim()}
                        style={{
                            ...styles.sendBtn,
                            ...(loading || !question.trim() ? styles.btnDisabled : {}),
                        }}
                    >
                        {loading ? "…" : "Envoyer"}
                    </button>
                </div>
            </section>
        </div>
    );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = {
    container: {
        maxWidth: "820px",
        margin: "0 auto",
        padding: "28px 16px",
        fontFamily: "'Segoe UI', Arial, sans-serif",
        color: "#1a1a1a",
    },
    title: {
        fontSize: "22px",
        fontWeight: "700",
        marginBottom: "24px",
    },

    // Upload
    uploadSection: {
        background: "#f9fafb",
        border: "1px solid #e5e7eb",
        borderRadius: "10px",
        padding: "16px 20px",
        marginBottom: "20px",
    },
    sectionTitle: {
        fontSize: "15px",
        fontWeight: "600",
        margin: "0 0 6px 0",
    },
    hint: {
        fontSize: "13px",
        color: "#6b7280",
        margin: "0 0 12px 0",
    },
    uploadRow: {
        display: "flex",
        gap: "10px",
        flexWrap: "wrap",
        alignItems: "center",
    },
    fileLabel: {
        display: "inline-block",
        padding: "7px 14px",
        border: "1px solid #d1d5db",
        borderRadius: "6px",
        cursor: "pointer",
        fontSize: "14px",
        background: "#fff",
        userSelect: "none",
    },
    btn: {
        padding: "7px 18px",
        background: "#2563eb",
        color: "#fff",
        border: "none",
        borderRadius: "6px",
        cursor: "pointer",
        fontWeight: "500",
        fontSize: "14px",
    },
    btnDisabled: {
        background: "#93c5fd",
        cursor: "not-allowed",
    },
    successMsg: { marginTop: "10px", color: "#15803d", fontSize: "13px" },
    errorMsg: { marginTop: "10px", color: "#dc2626", fontSize: "13px" },

    // Chat
    chatSection: {
        border: "1px solid #e5e7eb",
        borderRadius: "10px",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
    },
    chatHeader: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 20px",
        borderBottom: "1px solid #e5e7eb",
        background: "#f9fafb",
    },
    clearBtn: {
        background: "none",
        border: "1px solid #d1d5db",
        borderRadius: "5px",
        cursor: "pointer",
        fontSize: "12px",
        padding: "4px 10px",
        color: "#6b7280",
    },
    messageList: {
        minHeight: "320px",
        maxHeight: "520px",
        overflowY: "auto",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
    },
    emptyState: {
        color: "#9ca3af",
        textAlign: "center",
        margin: "auto",
        alignSelf: "center",
        fontSize: "14px",
    },
    humanBubble: {
        alignSelf: "flex-end",
        background: "#2563eb",
        color: "#fff",
        padding: "10px 14px",
        borderRadius: "14px 14px 2px 14px",
        maxWidth: "72%",
    },
    aiBubble: {
        alignSelf: "flex-start",
        background: "#f3f4f6",
        padding: "10px 14px",
        borderRadius: "14px 14px 14px 2px",
        maxWidth: "85%",
    },
    msgContent: {
        margin: 0,
        whiteSpace: "pre-wrap",
        lineHeight: "1.55",
        fontSize: "15px",
    },

    // Sources
    sourcesDetails: { marginTop: "8px" },
    sourcesSummary: {
        cursor: "pointer",
        fontSize: "12px",
        color: "#6b7280",
        userSelect: "none",
    },
    sourcesList: { marginTop: "6px", display: "flex", flexDirection: "column", gap: "6px" },
    sourceItem: {
        background: "#fff",
        border: "1px solid #e5e7eb",
        borderRadius: "6px",
        padding: "6px 10px",
        fontSize: "12px",
    },
    sourceFilename: { fontWeight: "600" },
    sourcePage: { color: "#6b7280" },
    sourceExcerpt: {
        margin: "4px 0 0 0",
        color: "#6b7280",
        fontStyle: "italic",
        lineHeight: "1.4",
    },

    // Input
    inputRow: {
        display: "flex",
        gap: "10px",
        padding: "12px 16px",
        borderTop: "1px solid #e5e7eb",
        alignItems: "flex-end",
    },
    textarea: {
        flex: 1,
        padding: "10px 12px",
        fontSize: "14px",
        border: "1px solid #d1d5db",
        borderRadius: "8px",
        resize: "none",
        outline: "none",
        fontFamily: "inherit",
        lineHeight: "1.5",
    },
    sendBtn: {
        padding: "10px 20px",
        background: "#2563eb",
        color: "#fff",
        border: "none",
        borderRadius: "8px",
        cursor: "pointer",
        fontWeight: "600",
        fontSize: "14px",
        height: "44px",
        minWidth: "80px",
    },
};
