package at.computor.keycloak.abuse;

import java.util.List;
import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.authentication.Authenticator;
import org.keycloak.authentication.authenticators.resetcred.ResetCredentialChooseUser;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.DefaultActionTokenKey;
import org.keycloak.provider.ProviderConfigProperty;

/** Replaces Choose User; preserves stock generic reset behavior after checking proof of work. */
public final class ResetAbuse extends ResetCredentialChooseUser {
    public static final String ID = "computor-reset-abuse";
    @Override public String getId() { return ID; }
    @Override public String getDisplayType() { return "Computor protected password reset"; }
    @Override public String getHelpText() { return "Replace Choose User with session-bound ALTCHA and honeypot before reset email."; }
    @Override public boolean isConfigurable() { return true; }
    @Override public List<ProviderConfigProperty> getConfigProperties() { return ProofOfWork.configProperties(); }
    @Override public Authenticator create(KeycloakSession session) { return this; }
    @Override public void authenticate(AuthenticationFlowContext context) {
        // The already-signed reset-email action token continues the reset without issuing another email.
        if (context.getAuthenticationSession().getAuthNote(DefaultActionTokenKey.ACTION_TOKEN_USER_ID) != null) {
            super.authenticate(context);
            return;
        }
        challenge(context, false);
    }
    private void challenge(AuthenticationFlowContext context, boolean failed) {
        var form = context.form();
        ProofOfWork.build(context.getSession(), context.getAuthenticationSession(), context.getAuthenticatorConfig(), "reset", form);
        if (failed) form.setError("computorAbuseVerificationFailed");
        context.challenge(form.createPasswordReset());
    }
    @Override public void action(AuthenticationFlowContext context) {
        var data = context.getHttpRequest().getDecodedFormParameters();
        boolean verified = ProofOfWork.verify(context.getSession(), context.getAuthenticationSession(), context.getAuthenticatorConfig(), "reset", data.getFirst("altcha"), data.getFirst("website"));
        data.remove("altcha"); data.remove("website");
        if (!verified) { challenge(context, true); return; }
        String username = data.getFirst("username");
        if (username == null || username.isBlank()) { challenge(context, true); return; }
        // Canonical aliases can recover only one verified account; ambiguous/unverified matches stay generic.
        String canonical = GmailAddress.canonical(username);
        if (canonical != null) {
            var matches = GmailUniqueValidator.matches(context.getSession(), context.getRealm().getId(), canonical);
            if (matches.size() == 1 && matches.get(0).verified()) data.putSingle("username", matches.get(0).email());
        }
        super.action(context);
    }
}
