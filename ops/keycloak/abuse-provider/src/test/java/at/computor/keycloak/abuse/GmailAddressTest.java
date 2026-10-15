package at.computor.keycloak.abuse;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

class GmailAddressTest {
    @Test void dotsTagsAndCaseShareOneConsumerInbox() {
        assertEquals("firstlast@gmail.com", GmailAddress.canonical("First.Last+course@gmail.com"));
        assertEquals(GmailAddress.canonical("fi.wo.ko.g.ut.u.ka9.8@gmail.com"), GmailAddress.canonical("fiw.o.k.ogu.tuka.9.8@gmail.com"));
    }
    @Test void otherProvidersAndWorkspaceAreNotRewritten() {
        assertNull(GmailAddress.canonical("first.last+course@example.com"));
        assertNull(GmailAddress.canonical("first.last@googlemail.com"));
        assertNull(GmailAddress.canonical("first.last@gmail.com.example.com"));
    }
    @Test void malformedConsumerAddressesAreLeftToEmailValidator() {
        assertNull(GmailAddress.canonical("+tag@gmail.com"));
        assertNull(GmailAddress.canonical("evil@first@gmail.com"));
        assertNull(GmailAddress.canonical(null));
    }
}
