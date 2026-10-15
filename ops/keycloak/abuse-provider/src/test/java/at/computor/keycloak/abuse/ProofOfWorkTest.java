package at.computor.keycloak.abuse;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import java.nio.charset.StandardCharsets;
import java.nio.ByteBuffer;
import java.util.*;
import java.util.concurrent.*;
import org.altcha.altcha.v2.Altcha;
import org.json.JSONObject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.*;
import org.keycloak.sessions.*;

class ProofOfWorkTest {
    final KeycloakSession session = mock(KeycloakSession.class);
    final SingleUseObjectProvider store = mock(SingleUseObjectProvider.class);
    final AuthenticationSessionModel auth = mock(AuthenticationSessionModel.class);
    final LoginFormsProvider form = mock(LoginFormsProvider.class);
    final AuthenticatorConfigModel config = new AuthenticatorConfigModel();
    final Map<String, String> notes = new ConcurrentHashMap<>();
    final Map<String, Map<String, String>> tokens = new ConcurrentHashMap<>();
    final Map<String, Object> attributes = new ConcurrentHashMap<>();

    @BeforeEach void configure() {
        config.setConfig(Map.of("secret", "test-only-secret-that-is-at-least-thirty-two-characters", "cost", "1000", "ttlSeconds", "300"));
        when(session.singleUseObjects()).thenReturn(store);
        var parent = mock(RootAuthenticationSessionModel.class);
        when(parent.getId()).thenReturn("root-1"); when(auth.getParentSession()).thenReturn(parent); when(auth.getTabId()).thenReturn("tab-1");
        when(auth.getAuthNote(anyString())).thenAnswer(i -> notes.get(i.getArgument(0)));
        doAnswer(i -> { notes.put(i.getArgument(0), i.getArgument(1)); return null; }).when(auth).setAuthNote(anyString(), anyString());
        doAnswer(i -> { notes.remove(i.getArgument(0)); return null; }).when(auth).removeAuthNote(anyString());
        doAnswer(i -> { tokens.put(i.getArgument(0), i.getArgument(2)); return null; }).when(store).put(anyString(), anyLong(), anyMap());
        when(store.remove(anyString())).thenAnswer(i -> tokens.remove(i.getArgument(0)));
        when(form.setAttribute(anyString(), any())).thenAnswer(i -> { attributes.put(i.getArgument(0), i.getArgument(1)); return form; });
    }

    String solve() throws Exception {
        ProofOfWork.build(session, auth, config, "registration", form);
        String json = (String) attributes.get("computorAltchaChallenge");
        // parsePayload consumes the same encoded JSON the browser submits.
        String shell = Base64.getEncoder().encodeToString(("{\"challenge\":" + json + ",\"solution\":{\"counter\":0,\"derivedKey\":\"00\",\"time\":0}}").getBytes(StandardCharsets.UTF_8));
        var challenge = Altcha.parsePayload(shell).challenge();
        var solution = Altcha.solveChallenge(challenge, Altcha.kdf("PBKDF2/SHA-256"));
        String payload = "{\"challenge\":" + json + ",\"solution\":{\"counter\":" + solution.counter() + ",\"derivedKey\":\"" + solution.derivedKey() + "\",\"time\":0}}";
        return Base64.getEncoder().encodeToString(payload.getBytes(StandardCharsets.UTF_8));
    }

    @Test void validSolutionConsumedOnce() throws Exception {
        String proof = solve();
        assertTrue(ProofOfWork.verify(session, auth, config, "registration", proof, ""));
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", proof, ""));
    }
    @Test void flowAndSessionBindingRejectStolenSolution() throws Exception {
        String proof = solve();
        assertFalse(ProofOfWork.verify(session, auth, config, "reset", proof, ""));
        var other = mock(AuthenticationSessionModel.class);
        assertFalse(ProofOfWork.verify(session, other, config, "registration", proof, ""));
        assertTrue(ProofOfWork.verify(session, auth, config, "registration", proof, ""));
    }
    @Test void honeypotAndBoundedMalformedPayloadFail() throws Exception {
        String proof = solve();
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", proof, "bot"));
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", "A".repeat(8193), ""));
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", "!", ""));
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", null, ""));
        assertTrue(ProofOfWork.verify(session, auth, config, "registration", proof, ""));
    }
    @Test void expiredStoreEntryCannotBeReplayed() throws Exception {
        String proof = solve(); tokens.clear();
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", proof, ""));
    }
    @Test void tamperedSolutionAndSignatureFail() throws Exception {
        String proof = solve();
        var payload = new JSONObject(new String(Base64.getDecoder().decode(proof), StandardCharsets.UTF_8));
        payload.getJSONObject("solution").put("derivedKey", "00".repeat(32));
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", Base64.getEncoder().encodeToString(payload.toString().getBytes(StandardCharsets.UTF_8)), ""));
        payload.getJSONObject("challenge").put("signature", "bad");
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", Base64.getEncoder().encodeToString(payload.toString().getBytes(StandardCharsets.UTF_8)), ""));
    }
    @Test void correctButNonsolvingDerivedKeyCannotBypassProofOfWork() throws Exception {
        String proof = solve();
        var payload = Altcha.parsePayload(proof);
        var params = payload.challenge().parameters();
        byte[] nonce = HexFormat.of().parseHex(params.nonce());
        byte[] salt = HexFormat.of().parseHex(params.salt());
        for (int counter = 0; counter < 100; counter++) {
            var password = ByteBuffer.allocate(nonce.length + 4).put(nonce).putInt(counter).array();
            String key = HexFormat.of().formatHex(Altcha.kdf("PBKDF2/SHA-256").deriveKey(params, salt, password).derivedKey());
            if (key.startsWith(params.keyPrefix())) continue;
            var forged = new JSONObject(new String(Base64.getDecoder().decode(proof), StandardCharsets.UTF_8));
            forged.getJSONObject("solution").put("counter", counter).put("derivedKey", key);
            String encoded = Base64.getEncoder().encodeToString(forged.toString().getBytes(StandardCharsets.UTF_8));
            // Upstream 2.0.1 accepts re-derived keys without checking challenge difficulty; guard that explicitly.
            assertTrue(Altcha.verifySolution(encoded, ProofOfWork.settings(config).secret(), Altcha.kdf("PBKDF2/SHA-256")).verified());
            assertFalse(ProofOfWork.verify(session, auth, config, "registration", encoded, ""));
            return;
        }
        fail("Could not find a nonsolving counter");
    }
    @Test void retryBuildInvalidatesPreviousChallenge() throws Exception {
        String first = solve(); String second = solve();
        assertFalse(ProofOfWork.verify(session, auth, config, "registration", first, ""));
        assertTrue(ProofOfWork.verify(session, auth, config, "registration", second, ""));
    }
    @Test void parallelConsumptionHasExactlyOneWinner() throws Exception {
        String proof = solve();
        try (var executor = Executors.newFixedThreadPool(4)) {
            var jobs = new ArrayList<Callable<Boolean>>();
            for (int i = 0; i < 8; i++) jobs.add(() -> ProofOfWork.verify(session, auth, config, "registration", proof, ""));
            assertEquals(1, executor.invokeAll(jobs).stream().filter(f -> { try { return f.get(); } catch (Exception e) { throw new RuntimeException(e); } }).count());
        }
    }
    @Test void secretAndCostConfigurationFailClosed() {
        config.setConfig(Map.of("secret", "too-short"));
        assertThrows(IllegalStateException.class, () -> ProofOfWork.settings(config));
        ProofOfWork.build(session, auth, config, "registration", form);
        assertNull(notes.get(ProofOfWork.NOTE_PREFIX + "registration"));
        verify(form).setError("computorAbuseUnavailable");
    }
}
