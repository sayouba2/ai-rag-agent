const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export async function askQuestion(question, sessionId = null) {
    const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionId }),
    });

    if (!res.ok) throw new Error("Failed to get answer");
    return res.json();
}

/**
 * Streaming SSE via /ask/stream.
 *
 * @param {string}   question
 * @param {string|null} sessionId  - null pour une nouvelle session
 * @param {(token: string) => void} onToken    - appelé pour chaque token
 * @param {(sources: object[]) => void} onSources - appelé avec la liste des sources
 * @param {(sessionId: string) => void} onDone  - appelé à la fin du stream
 */
export async function askQuestionStream(question, sessionId, onToken, onSources, onDone) {
    const res = await fetch(`${API_BASE}/ask/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionId }),
    });

    if (!res.ok) throw new Error("Failed to start stream");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let currentSessionId = sessionId;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Les événements SSE sont séparés par "\n\n"
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
            if (!part.startsWith("data: ")) continue;
            const raw = part.slice(6).trim();

            if (raw === "[DONE]") {
                onDone(currentSessionId);
                return;
            }

            try {
                const event = JSON.parse(raw);
                if (event.type === "session_id") currentSessionId = event.session_id;
                else if (event.type === "token") onToken(event.content);
                else if (event.type === "sources") onSources(event.sources);
            } catch {
                // chunk JSON incomplet ou invalide — on ignore
            }
        }
    }

    onDone(currentSessionId);
}

export async function uploadFiles(files) {
    const formData = new FormData();
    for (const file of files) {
        formData.append("files", file);
    }

    const res = await fetch(`${API_BASE}/upload`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload échoué." }));
        throw new Error(err.detail ?? "Upload échoué.");
    }

    return res.json();
}

export async function clearHistory(sessionId) {
    await fetch(`${API_BASE}/history/${sessionId}`, { method: "DELETE" });
}
