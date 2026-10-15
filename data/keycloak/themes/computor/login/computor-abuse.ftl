<#macro challenge>
    <#if computorAltchaRequired!false>
        <div hidden aria-hidden="true">
            <label for="computor-website">Website</label>
            <input type="text" id="computor-website" name="website" value="" tabindex="-1" autocomplete="off"/>
        </div>
        <div class="${properties.kcFormGroupClass!}">
            <#if computorAltchaChallenge??>
                <altcha-widget challenge="${computorAltchaChallenge}" auto="onload" language="${(locale.currentLanguageTag)!'en'}"></altcha-widget>
            <#else>
                <p role="alert">${msg("computorAbuseUnavailable")}</p>
            </#if>
            <noscript><p>${msg("computorJavascriptRequired")}</p></noscript>
        </div>
        <script type="module" src="${url.resourcesPath}/js/computor-altcha-20261016.js"></script>
    </#if>
</#macro>
