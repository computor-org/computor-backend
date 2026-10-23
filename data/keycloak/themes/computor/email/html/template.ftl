<#--
  Computor frame for every HTML mail Keycloak sends (issues#478): the realm name
  as a header in the web UI's colours, the message on a white card, and a
  footer saying the mail was sent automatically. Inline styles and a table
  layout, because mail clients drop most of a <style> block. Links inside the
  message become buttons where the client honours the <style> block; elsewhere
  they stay ordinary blue links. No deployment-specific address or image, so
  the same theme serves every instance.
-->
<#macro emailLayout>
<!DOCTYPE html>
<html lang="${locale.language}" dir="${(ltr)?then('ltr','rtl')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<style>
  .ct-body a { display: inline-block; margin: 4px 0; padding: 10px 18px; border-radius: 8px;
    background: #2563eb; color: #ffffff !important; font-weight: 600; text-decoration: none; }
  .ct-body p:first-child { margin-top: 0; }
  .ct-body p:last-child { margin-bottom: 0; }
</style>
</head>
<body style="margin:0; padding:0; background:#f3f4f6;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;">
  <tr><td align="center" style="padding:32px 16px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
      <tr><td style="padding:0 4px 16px; font-family:system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;">
        <span style="display:inline-block; width:12px; height:28px; margin-right:10px; vertical-align:middle; background:#e8003d; border-radius:2px;"></span><span style="vertical-align:middle; font-size:22px; font-weight:700; color:#111827;">${realmName}</span>
      </td></tr>
      <tr><td class="ct-body" style="background:#ffffff; border:1px solid #e5e7eb; border-radius:12px; padding:28px; font-family:system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif; font-size:16px; line-height:1.55; color:#1f2937;">
        <#nested>
      </td></tr>
      <tr><td style="padding:16px 4px 0; font-family:system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif; font-size:13px; line-height:1.5; color:#6b7280;">
        ${msg("computorMailFooter", realmName)}
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>
</#macro>
