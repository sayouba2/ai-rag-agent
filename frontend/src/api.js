const API_BASE = "http://127.0.0.1:8000";

export async function askQuestion(question) {
    const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
    });

    if (!res.ok) {
        throw new Error("Failed to get answer");
    }

    return res.json();
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
        throw new Error("Failed to upload files");
    }

    return res.json();
}