package at.computor.keycloak.abuse;

import org.keycloak.Config;
import org.keycloak.events.*;
import org.keycloak.events.admin.AdminEvent;
import org.keycloak.models.*;

/** Server-owned login provenance used by conservative orphan-account cleanup. */
public final class ActivityListener implements EventListenerProviderFactory {
    public static final String ID = "computor-registration-activity";
    @Override public String getId() { return ID; }
    @Override public EventListenerProvider create(KeycloakSession session) {
        return new EventListenerProvider() {
            @Override public void onEvent(Event event) {
                if (event.getType() != EventType.LOGIN || event.getUserId() == null) return;
                RealmModel realm = session.realms().getRealm(event.getRealmId());
                if (realm == null) return;
                UserModel user = session.users().getUserById(realm, event.getUserId());
                if (user != null && "true".equals(user.getFirstAttribute("computor.selfRegistered"))) {
                    user.setSingleAttribute("computor.lastLogin", Long.toString(event.getTime()));
                }
            }
            @Override public void onEvent(AdminEvent event, boolean includeRepresentation) { }
            @Override public void close() { }
        };
    }
    @Override public void init(Config.Scope config) { }
    @Override public void postInit(KeycloakSessionFactory factory) { }
    @Override public void close() { }
}
