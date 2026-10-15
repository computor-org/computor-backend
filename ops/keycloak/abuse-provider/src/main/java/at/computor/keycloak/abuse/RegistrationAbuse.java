package at.computor.keycloak.abuse;

import java.util.List;
import org.keycloak.Config;
import org.keycloak.authentication.*;
import org.keycloak.events.Errors;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.*;
import org.keycloak.models.utils.FormMessage;
import org.keycloak.provider.ProviderConfigProperty;

public final class RegistrationAbuse implements FormAction, FormActionFactory {
    public static final String ID = "computor-registration-abuse";
    @Override public void buildPage(FormContext context, LoginFormsProvider form) {
        ProofOfWork.build(context.getSession(), context.getAuthenticationSession(), context.getAuthenticatorConfig(), "registration", form);
    }
    @Override public void validate(ValidationContext context) {
        var data = context.getHttpRequest().getDecodedFormParameters();
        boolean verified = ProofOfWork.verify(context.getSession(), context.getAuthenticationSession(), context.getAuthenticatorConfig(), "registration", data.getFirst("altcha"), data.getFirst("website"));
        data.remove("altcha"); data.remove("website");
        if (verified) context.success();
        else {
            context.error(Errors.INVALID_REGISTRATION);
            context.validationError(data, List.of(new FormMessage("computorAbuseVerificationFailed")));
        }
    }
    @Override public void success(FormContext context) {
        // This action must follow Registration User Creation, so only server-created users get provenance.
        if (context.getUser() != null) {
            context.getUser().setSingleAttribute("computor.selfRegistered", "true");
            context.getUser().setSingleAttribute("computor.selfRegisteredAt", Long.toString(context.getUser().getCreatedTimestamp()));
        }
    }
    @Override public String getId() { return ID; }
    @Override public String getDisplayType() { return "Computor registration abuse protection"; }
    @Override public String getHelpText() { return "Session-bound ALTCHA proof of work and honeypot, required after user creation action."; }
    @Override public String getReferenceCategory() { return "computor-abuse"; }
    @Override public boolean isConfigurable() { return true; }
    @Override public boolean isUserSetupAllowed() { return false; }
    @Override public AuthenticationExecutionModel.Requirement[] getRequirementChoices() { return new AuthenticationExecutionModel.Requirement[]{AuthenticationExecutionModel.Requirement.REQUIRED, AuthenticationExecutionModel.Requirement.DISABLED}; }
    @Override public List<ProviderConfigProperty> getConfigProperties() { return ProofOfWork.configProperties(); }
    @Override public FormAction create(KeycloakSession session) { return this; }
    @Override public boolean requiresUser() { return false; }
    @Override public boolean configuredFor(KeycloakSession s, RealmModel r, UserModel u) { return true; }
    @Override public void setRequiredActions(KeycloakSession s, RealmModel r, UserModel u) { }
    @Override public void init(Config.Scope config) { }
    @Override public void postInit(KeycloakSessionFactory factory) { }
    @Override public void close() { }
}
