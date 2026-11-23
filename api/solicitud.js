// Recibe las solicitudes de consejo asesor y las reenvía por correo desde tu propia cuenta de Gmail (gratis).
// Ni el correo ni la contraseña aparecen en la web: se guardan en las variables de entorno de Vercel.
//   GMAIL_USER          cuenta de Gmail que envía las solicitudes
//   GMAIL_APP_PASSWORD  contraseña de aplicación de esa cuenta (myaccount.google.com/apppasswords)
//   CONTACT_EMAIL       opcional; correo que recibe las solicitudes (por defecto, GMAIL_USER)

const nodemailer = require("nodemailer");

const clean = (v, max) => String(v || "").replace(/[\r\n]+/g, " ").trim().slice(0, max);

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false });
  }

  const { GMAIL_USER, GMAIL_APP_PASSWORD } = process.env;
  const CONTACT_EMAIL = process.env.CONTACT_EMAIL || GMAIL_USER;
  if (!GMAIL_USER || !GMAIL_APP_PASSWORD) {
    return res.status(503).json({ ok: false, error: "not_configured" });
  }

  let body = req.body || {};
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }

  // Campo trampa para bots: las personas no lo ven ni lo rellenan.
  if (body.website) return res.status(200).json({ ok: true });

  const name = clean(body.name, 120);
  const email = clean(body.email, 200);
  const phone = clean(body.phone, 35);
  const project = clean(body.project, 200);
  const stage = clean(body.stage, 60);
  const msg = String(body.msg || "").trim().slice(0, 3000);

  if (!name || !project || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) || phone.replace(/\D/g, "").length < 7) {
    return res.status(400).json({ ok: false, error: "invalid" });
  }

  const text = [
    `Nombre: ${name}`,
    `Email: ${email}`,
    `Móvil: ${phone}`,
    `Proyecto: ${project}`,
    `Etapa del proyecto: ${stage}`,
    "",
    "Mensaje:",
    msg || "(sin indicar)",
  ].join("\n");

  try {
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: { user: GMAIL_USER, pass: GMAIL_APP_PASSWORD.replace(/\s+/g, "") },
    });
    await transporter.sendMail({
      from: `"Branka" <${GMAIL_USER}>`,
      to: CONTACT_EMAIL,
      replyTo: `"${name.replace(/"/g, "")}" <${email}>`,
      subject: `Branka · Solicitud de consejo asesor · ${project}`,
      text,
    });
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error("send_failed", err && err.message);
    return res.status(502).json({ ok: false, error: "send_failed" });
  }
};
