const SYSTEM_PROMPT = `
You are an EBT application assistant helping clients apply for food assistance benefits.
Keep every reply under 3 sentences because responses may be spoken aloud.
Never use bullet points, markdown, or special characters.
Speak naturally, like a conversation.
Do not ask for or repeat back sensitive personal information such as Social Security numbers, bank account details, or passwords.
If user asks to switch language, return responses in that language.
`;

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ error: "GROQ_API_KEY is not configured." });
  }

  const { messages = [] } = req.body || {};
  const safeMessages = messages
    .filter((message) => message && ["user", "assistant"].includes(message.role))
    .slice(-12)
    .map((message) => ({
      role: message.role,
      content: String(message.content || "").slice(0, 2000),
    }));

  try {
    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        max_tokens: 512,
        messages: [{ role: "system", content: SYSTEM_PROMPT.trim() }, ...safeMessages],
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      return res.status(response.status).json({
        error: data?.error?.message || "Groq request failed.",
      });
    }

    return res.status(200).json({
      reply: data.choices?.[0]?.message?.content?.trim() || "Sorry, I did not get a response.",
    });
  } catch (error) {
    return res.status(500).json({ error: "Unable to reach the AI service." });
  }
};
