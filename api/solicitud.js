// Recibe las solicitudes de mentoría (y de quien quiere ser mentor) y las reenvía por correo con Resend.
// El correo de destino nunca aparece en la web: se guarda en las variables de entorno de Vercel.
//   RESEND_API_KEY  clave de API de Resend (resend.com)
//   CONTACT_EMAIL   correo que recibe las solicitudes
//   FROM_EMAIL      opcional; remitente verificado en Resend (por defecto onboarding@resend.dev)

const clean = (v, max) => String(v || "").replace(/[\r\n]+/g, " ").trim().slice(0, max);

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false });
  }

  const { RESEND_API_KEY, CONTACT_EMAIL, FROM_EMAIL } = process.env;
  if (!RESEND_API_KEY || !CONTACT_EMAIL) {
    return res.status(503).json({ ok: false, error: "not_configured" });
  }

  let body = req.body || {};
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { body = {}; }
  }

  // Campo trampa para bots: las personas no lo ven ni lo rellenan.
  if (body.website) return res.status(200).json({ ok: true });

  const role = clean(body.role, 40) || "Tener un mentor";
  const name = clean(body.name, 120);
  const email = clean(body.email, 200);
  const project = clean(body.project, 200);
  const stage = clean(body.stage, 60);
  const msg = String(body.msg || "").trim().slice(0, 3000);

  if (!name || !project || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return res.status(400).json({ ok: false, error: "invalid" });
  }

  const text = [
    `Quiere: ${role}`,
    `Nombre: ${name}`,
    `Email: ${email}`,
    `Proyecto: ${project}`,
    `Etapa / experiencia: ${stage}`,
    "",
    "Mensaje:",
    msg || "(sin indicar)",
  ].join("\n");

  try {
    const r = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${RESEND_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: FROM_EMAIL || "Branka <onboarding@resend.dev>",
        to: [CONTACT_EMAIL],
        reply_to: email,
        subject: `Branka · ${role === "Ser mentor/a" ? "Nuevo mentor" : "Solicitud de mentoría"} · ${project}`,
        text,
      }),
    });
    if (!r.ok) return res.status(502).json({ ok: false, error: "send_failed" });
    return res.status(200).json({ ok: true });
  } catch {
    return res.status(502).json({ ok: false, error: "send_failed" });
  }
};
