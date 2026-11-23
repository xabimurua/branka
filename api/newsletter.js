// Recibe altas a la newsletter y avisa por correo con la misma cuenta de Gmail del formulario.
// Variables de entorno en Vercel (las mismas que api/solicitud.js):
//   GMAIL_USER, GMAIL_APP_PASSWORD, CONTACT_EMAIL (opcional)
// Cada alta llega como un correo con el asunto "Branka · Newsletter · alta".

const nodemailer = require("nodemailer");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false });
  }
  const { GMAIL_USER, GMAIL_APP_PASSWORD } = process.env;
  const CONTACT_EMAIL = process.env.CONTACT_EMAIL || GMAIL_USER;
  if (!GMAIL_USER || !GMAIL_APP_PASSWORD) return res.status(503).json({ ok: false, error: "not_configured" });

  let body = req.body || {};
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = {}; } }
  if (body.website) return res.status(200).json({ ok: true });

  const email = String(body.email || "").replace(/[\r\n]+/g, " ").trim().slice(0, 200);
  const from = String(body.from || "").replace(/[\r\n]+/g, " ").trim().slice(0, 60);
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return res.status(400).json({ ok: false, error: "invalid" });

  try {
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: { user: GMAIL_USER, pass: GMAIL_APP_PASSWORD.replace(/\s+/g, "") },
    });
    await transporter.sendMail({
      from: `"Branka" <${GMAIL_USER}>`,
      to: CONTACT_EMAIL,
      replyTo: email,
      subject: "Branka · Newsletter · alta",
      text: `Nueva suscripción a la newsletter\n\nEmail: ${email}\nDesde: ${from || "web"}\nFecha: ${new Date().toISOString()}`,
    });
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("send_failed", err && err.message);
    return res.status(502).json({ ok: false, error: "send_failed" });
  }
};
