package at.computor.keycloak.abuse;

import java.util.List;
import jakarta.persistence.LockModeType;
import org.keycloak.connections.jpa.JpaConnectionProvider;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.jpa.entities.RealmEntity;
import org.keycloak.services.messages.Messages;
import org.keycloak.userprofile.UserProfileAttributeValidationContext;
import org.keycloak.validate.*;

/**
 * Canonical uniqueness enforced inside the user-profile mutation transaction.
 * The persisted realm row is a cluster-wide serialization point, held until commit/rollback.
 * No cache or asynchronous event listener is involved in the uniqueness decision.
 */
public final class GmailUniqueValidator extends AbstractStringValidator {
    public static final String ID = "computor-gmail-unique";
    @Override public String getId() { return ID; }
    @Override protected boolean skipValidation(Object value, ValidatorConfig config) {
        return value == null || value instanceof String && ((String) value).isBlank();
    }

    @Override protected void doValidate(String value, String inputHint, ValidationContext context, ValidatorConfig config) {
        String canonical = GmailAddress.canonical(value);
        if (canonical == null) return;
        var attribute = UserProfileAttributeValidationContext.from(context).getAttributeContext();
        var current = attribute.getUser();
        // Existing audited collisions retain their account; saving unrelated profile changes remains possible.
        if (current != null && canonical.equals(GmailAddress.canonical(current.getEmail()))) return;
        var session = attribute.getSession();
        String realmId = session.getContext().getRealm().getId();
        var em = session.getProvider(JpaConnectionProvider.class).getEntityManager();
        em.find(RealmEntity.class, realmId, LockModeType.PESSIMISTIC_WRITE);
        if (matches(session, realmId, canonical).stream().anyMatch(user -> current == null || !user.id().equals(current.getId()))) {
            context.addError(new ValidationError(ID, inputHint, Messages.EMAIL_EXISTS));
        }
    }

    record Match(String id, String email, boolean verified) { }

    static List<Match> matches(KeycloakSession session, String realmId, String canonical) {
        // Query scalar persisted state, bypassing Keycloak's distributed user cache and JPA entity identity cache.
        var rows = session.getProvider(JpaConnectionProvider.class).getEntityManager()
            .createQuery("select u.id, u.email, u.emailVerified from UserEntity u where u.realmId = :realm and lower(u.email) like :domain", Object[].class)
            .setParameter("realm", realmId).setParameter("domain", "%@gmail.com").getResultList();
        return rows.stream().filter(row -> canonical.equals(GmailAddress.canonical((String) row[1])))
            .map(row -> new Match((String) row[0], (String) row[1], (Boolean) row[2])).toList();
    }
}
