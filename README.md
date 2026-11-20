# Branka · Monta tu consejo asesor

Web estática (HTML, sin compilación). Lo central son los consejos asesores: emprendedores con experiencia que acompañan a quienes empiezan. Como apoyo incluye:

- **Herramientas**: 17 herramientas explicadas en 1 minuto, con plantilla descargable en PDF (`plantillas/`).
- **Aprende**: los episodios más vistos del podcast de Itnig, reproducibles en la página.
- **Noticias**: actualidad de tecnología y negocios con una lección para emprendedores.


Se despliega en Vercel como sitio estático: cada cambio en `main` se publica solo.

## Formulario de solicitud

Las solicitudes se envían a `/api/solicitud`, una función de Vercel que las reenvía por correo con [Resend](https://resend.com). El correo de destino no aparece en la web: se configura en Vercel → Settings → Environment Variables con `RESEND_API_KEY` y `CONTACT_EMAIL` (y, opcionalmente, `FROM_EMAIL`).
