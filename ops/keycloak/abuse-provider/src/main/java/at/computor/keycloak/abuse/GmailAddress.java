package at.computor.keycloak.abuse;

import java.util.Locale;

final class GmailAddress {
    private GmailAddress() { }
    /** Only consumer gmail.com: other domains (including Workspace) retain their own rules. */
    static String canonical(String email) {
        if (email == null || email.length() > 320) return null;
        String value = email.trim().toLowerCase(Locale.ROOT);
        int at = value.lastIndexOf('@');
        if (at <= 0 || !value.substring(at + 1).equals("gmail.com")) return null;
        String local = value.substring(0, at);
        int tag = local.indexOf('+');
        if (tag >= 0) local = local.substring(0, tag);
        local = local.replace(".", "");
        // Only apply known consumer syntax; the normal email validator owns malformed inputs.
        if (!local.matches("[a-z0-9]+")) return null;
        return local + "@gmail.com";
    }
}
