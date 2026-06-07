module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: "GROQ_API_KEY is not configured." });
  }

  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }

  const audio = Buffer.concat(chunks);
  if (!audio.length) {
    return res.status(400).json({ error: "No audio was received." });
  }

  const contentType = req.headers["content-type"] || "audio/webm";
  const extension = contentType.includes("mp4")
    ? "mp4"
    : contentType.includes("mpeg")
      ? "mp3"
      : contentType.includes("ogg")
        ? "ogg"
        : "webm";

  const form = new FormData();
  form.append("model", "whisper-large-v3-turbo");
  form.append("response_format", "json");
  form.append("file", new Blob([audio], { type: contentType }), `voice-input.${extension}`);

  try {
    const response = await fetch("https://api.groq.com/openai/v1/audio/transcriptions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
      body: form,
    });

    const data = await response.json();
    if (!response.ok) {
      return res.status(response.status).json({
        error: data?.error?.message || "Groq transcription failed.",
      });
    }

    return res.status(200).json({ text: data.text?.trim() || "" });
  } catch (error) {
    return res.status(500).json({ error: "Unable to transcribe audio." });
  }
};
