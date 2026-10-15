package at.computor.keycloak.abuse;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;
import org.altcha.altcha.v2.Altcha;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.AuthenticatorConfigModel;
import org.keycloak.models.KeycloakSession;
import org.keycloak.provider.ProviderConfigProperty;
import org.keycloak.sessions.AuthenticationSessionModel;

/** Session-bound, expiring challenges; Keycloak's single-use store provides atomic cluster-wide consumption. */
final class ProofOfWork {
    static final int MAX_PAYLOAD = 8192;
    static final String NOTE_PREFIX = "computor.pow.";
    record Settings(String secret, int ttl, int cost) { }

    static Settings settings(AuthenticatorConfigModel model) {
        Map<String, String> config = model == null ? Map.of() : model.getConfig();
        if (config == null) config = Map.of();
        String secret = config.get("secret");
        if (secret == null || secret.length() < 32) throw new IllegalStateException("ALTCHA requires a secret of at least 32 characters");
        int ttl = bounded(config.getOrDefault("ttlSeconds", "300"), 30, 900);
        int cost = bounded(config.getOrDefault("cost", "10000"), 1000, 100000);
        return new Settings(secret, ttl, cost);
    }

    private static int bounded(String value, int minimum, int maximum) {
        int parsed = Integer.parseInt(value);
        if (parsed < minimum || parsed > maximum) throw new IllegalStateException("ALTCHA configuration outside allowed bounds");
        return parsed;
    }

    static List<ProviderConfigProperty> configProperties() {
        return List.of(new ProviderConfigProperty("secret", "ALTCHA secret", "Random shared secret, at least 32 characters.", ProviderConfigProperty.PASSWORD, null),
            new ProviderConfigProperty("ttlSeconds", "Challenge lifetime", "Seconds (30–900).", ProviderConfigProperty.STRING_TYPE, "300"),
            new ProviderConfigProperty("cost", "Proof cost", "PBKDF2/SHA-256 iterations (1000–100000).", ProviderConfigProperty.STRING_TYPE, "10000"));
    }

    static void build(KeycloakSession session, AuthenticationSessionModel auth, AuthenticatorConfigModel config,
                      String flow, LoginFormsProvider form) {
        try {
            Settings settings = settings(config);
            String old = auth.getAuthNote(NOTE_PREFIX + flow);
            if (old != null) session.singleUseObjects().remove(NOTE_PREFIX + old);
            var challenge = Altcha.createChallenge(new Altcha.CreateChallengeOptions()
                .algorithm("PBKDF2/SHA-256").cost(settings.cost()).expiresInSeconds(settings.ttl())
                .hmacSignatureSecret(settings.secret())
                .data(Map.of("session", auth.getParentSession().getId(), "tab", auth.getTabId(), "flow", flow)));
            String signature = challenge.signature();
            auth.setAuthNote(NOTE_PREFIX + flow, signature);
            session.singleUseObjects().put(NOTE_PREFIX + signature, settings.ttl(), Map.of("flow", flow));
            form.setAttribute("computorAltchaRequired", true);
            form.setAttribute("computorAltchaChallenge", challenge.toJson());
        } catch (Exception e) {
            // Fail closed: validate() cannot accept a missing challenge, even if the theme cannot render one.
            auth.removeAuthNote(NOTE_PREFIX + flow);
            form.setAttribute("computorAltchaRequired", true);
            form.setError("computorAbuseUnavailable");
        }
    }

    static boolean verify(KeycloakSession session, AuthenticationSessionModel auth, AuthenticatorConfigModel config,
                          String flow, String encoded, String honeypot) {
        if (honeypot != null && !honeypot.isEmpty()) return false;
        if (encoded == null || encoded.isBlank() || encoded.length() > MAX_PAYLOAD) return false;
        String expected = auth.getAuthNote(NOTE_PREFIX + flow);
        if (expected == null) return false;
        try {
            var payload = Altcha.parsePayload(encoded);
            String signature = payload.challenge().signature();
            if (!MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8), signature.getBytes(StandardCharsets.UTF_8))) return false;
            String prefix = payload.challenge().parameters().keyPrefix();
            if (prefix == null || prefix.isEmpty() || !payload.solution().derivedKey().startsWith(prefix)) return false;
            // Never run a client-selected KDF/cost: the signature must match our issued challenge first.
            if (!Altcha.verifySolution(encoded, settings(config).secret(), Altcha.kdf("PBKDF2/SHA-256")).verified()) return false;
            if (session.singleUseObjects().remove(NOTE_PREFIX + signature) == null) return false;
            auth.removeAuthNote(NOTE_PREFIX + flow);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
