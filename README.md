# Branka · Monta tu consejo asesor

Web estática (HTML, sin compilación). Lo central son los consejos asesores: emprendedores con experiencia que acompañan a quienes empiezan. Como apoyo incluye:

- **Herramientas**: 17 herramientas explicadas en 1 minuto, con plantilla descargable en PDF (`plantillas/`).
- **Aprende**: los episodios más vistos del podcast de Itnig, reproducibles en la página.
- **Noticias**: actualidad de tecnología y negocios con una lección para emprendedores.


Se despliega en Vercel como sitio estático: cada cambio en `main` se publica solo.

## Formulario de solicitud

Las solicitudes se envían a `/api/solicitud`, una función de Vercel que las reenvía por correo desde una cuenta de Gmail (gratis, con Nodemailer). Ni el correo ni la contraseña aparecen en la web: se configuran en Vercel → Settings → Environment Variables con `GMAIL_USER` y `GMAIL_APP_PASSWORD` (una contraseña de aplicación de Google) y, opcionalmente, `CONTACT_EMAIL` si las solicitudes deben llegar a otro correo.
