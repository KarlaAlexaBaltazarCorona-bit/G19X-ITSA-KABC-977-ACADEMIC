/**
 * auth.js — Lógica de autenticación con Microsoft Entra ID para PluriOne
 * ──────────────────────────────────────────────────────────────────────────────────
 *
 * FLUJO COMPLETO:
 *   1. initAuth()           → Obtiene parámetros de configuración del backend o localStorage.
 *   2. loginWithMicrosoft() → Inicia flujo popup de Microsoft Entra ID (o abre modal si no hay Client ID).
 *   3. Validación de Token  → Valida el JWT en /api/v1/auth/me y establece sesión en cookies.
 *   4. Redirección          → Envía al dashboard de la aplicación.
 *
 * MODAL DE CONEXIÓN DE ENTRA ID:
 *   - Permite ingresar el Application (client) ID de Azure directamente en pantalla.
 *   - Lo persiste en localStorage y en el servidor (.env) mediante /api/v1/auth/setup-client-id.
 *   - El botón principal NUNCA queda inhabilitado.
 */

// ─────────────────────────────────────────────────────────────────────────────
// CONFIGURACIÓN Y ESTADO GLOBAL
// ─────────────────────────────────────────────────────────────────────────────

let msalInstance = null;

let entraConfig = {
    clientId: "",
    authority: "https://login.microsoftonline.com/common"
};
let lastMsalError = "";

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS DEL DOM
// ─────────────────────────────────────────────────────────────────────────────

function getElements() {
    return {
        btnLogin:      document.getElementById("btn-login"),
        btnLabel:      document.getElementById("btn-label"),
        btnSpinner:    document.getElementById("btn-spinner"),
        msLogo:        document.getElementById("ms-logo"),
        statusError:   document.getElementById("status-error"),
        errorText:     document.getElementById("error-text"),
        statusSuccess: document.getElementById("status-success"),
        successText:   document.getElementById("success-text"),
        statusInfo:    document.getElementById("status-info"),
        infoText:      document.getElementById("info-text"),
        entraStatus:   document.getElementById("entra-id-status")
    };
}

function hideAlerts() {
    const el = getElements();
    if (el.statusError)   el.statusError.classList.add("hidden");
    if (el.statusSuccess) el.statusSuccess.classList.add("hidden");
    if (el.statusInfo)    el.statusInfo.classList.add("hidden");
}

function showError(msg) {
    hideAlerts();
    const el = getElements();
    if (el.errorText)   el.errorText.textContent = msg;
    if (el.statusError) el.statusError.classList.remove("hidden");
}

function showSuccess(msg) {
    hideAlerts();
    const el = getElements();
    if (el.successText)   el.successText.textContent = msg;
    if (el.statusSuccess) el.statusSuccess.classList.remove("hidden");
}

function showInfo(msg) {
    hideAlerts();
    const el = getElements();
    if (el.infoText)   el.infoText.textContent = msg;
    if (el.statusInfo) el.statusInfo.classList.remove("hidden");
}

function setLoading(isLoading, text) {
    const el = getElements();
    if (!el.btnLogin) return;
    el.btnLogin.disabled = isLoading;
    if (isLoading) {
        if (el.msLogo)     el.msLogo.classList.add("hidden");
        if (el.btnSpinner) el.btnSpinner.classList.remove("hidden");
        if (el.btnLabel)   el.btnLabel.textContent = text || "Conectando...";
    } else {
        if (el.msLogo)     el.msLogo.classList.remove("hidden");
        if (el.btnSpinner) el.btnSpinner.classList.add("hidden");
        if (el.btnLabel)   el.btnLabel.textContent = "Iniciar sesión con Microsoft";
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// INICIALIZACIÓN DE MSAL
// ─────────────────────────────────────────────────────────────────────────────

async function inicializarMSAL(clientId, authority) {
    if (!clientId) return false;

    if (!window.msal || !window.msal.PublicClientApplication) {
        console.warn("[PluriOne Auth] Librería msal-browser no disponible aún.");
        lastMsalError = "Librería msal-browser no disponible o bloqueada.";
        return false;
    }

    const msalConfig = {
        auth: {
            clientId:    clientId,
            authority:   authority || "https://login.microsoftonline.com/common",
            redirectUri: window.location.origin + "/login"
        },
        cache: {
            cacheLocation: "sessionStorage",
            storeAuthStateInCookie: false
        }
    };

    try {
        msalInstance = new window.msal.PublicClientApplication(msalConfig);
        if (msalInstance.initialize) {
            await msalInstance.initialize();
        }
        lastMsalError = "";
        return true;
    } catch (err) {
        console.error("[PluriOne Auth] Error al instanciar MSAL:", err);
        lastMsalError = err.message || String(err);
        return false;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// INICIALIZACIÓN PRINCIPAL: initAuth()
// ─────────────────────────────────────────────────────────────────────────────

async function initAuth() {
    const el = getElements();

    // Asegurarse de que el botón NUNCA esté inhabilitado
    if (el.btnLogin) {
        el.btnLogin.disabled = false;
    }

    try {
        // 1. Verificar si ya hay una sesión activa guardada
        const existingToken = sessionStorage.getItem("plurione_auth_token");
        if (existingToken) {
            try {
                const verifyRes = await fetch("/api/v1/auth/me", {
                    headers: { "Authorization": "Bearer " + existingToken }
                });
                if (verifyRes.ok) {
                    window.location.href = "/api/v1/app/dashboard";
                    return;
                }
            } catch (_) {}
        }

        // 2. Pedir configuración de Entra ID al servidor
        let serverClientId = "";
        try {
            const res = await fetch("/api/v1/auth/config");
            if (res.ok) {
                const data = await res.json();
                serverClientId = data.client_id || "";
                if (data.authority) {
                    entraConfig.authority = data.authority;
                }
            }
        } catch (e) {
            console.warn("[PluriOne Auth] No se pudo consultar /api/v1/auth/config:", e);
        }

        // Si el backend no tiene configurado el client_id, checar localStorage
        entraConfig.clientId = serverClientId || "";

        const isAzureProd = window.location.hostname.endsWith("azurewebsites.net");
        if (entraConfig.clientId) {
            await inicializarMSAL(entraConfig.clientId, entraConfig.authority);
            if (!isAzureProd) {
                const devPanel = document.getElementById("dev-login-panel");
                if (devPanel) devPanel.classList.remove("hidden");
            }
        } else {
            // No hay Client ID todavía (desarrollo local)
            const devPanel = document.getElementById("dev-login-panel");
            if (devPanel) {
                devPanel.classList.remove("hidden");
            }
            showInfo("Entorno de desarrollo local detectado (sin Entra ID). Selecciona un rol abajo para ingresar.");
        }

        // Garantizar botón activo
        if (el.btnLogin) el.btnLogin.disabled = false;

    } catch (err) {
        console.error("[PluriOne Auth] Error en initAuth:", err);
        if (el.btnLogin) el.btnLogin.disabled = false;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// FUNCIÓN DE LOGIN CON MICROSOFT
// ─────────────────────────────────────────────────────────────────────────────

async function loginWithMicrosoft() {
    hideAlerts();

    if (!entraConfig.clientId) {
        showInfo("Microsoft Entra ID no está configurado en local. Utilice el selector de Modo Desarrollo abajo.");
        const devPanel = document.getElementById("dev-login-panel");
        if (devPanel) devPanel.classList.remove("hidden");
        return;
    }

    // Si no está inicializado MSAL, intentar inicializarlo
    if (!msalInstance) {
        const ok = await inicializarMSAL(entraConfig.clientId, entraConfig.authority);
        if (!ok) {
            showError("No fue posible inicializar el componente de Microsoft Entra ID" + (lastMsalError ? `: ${lastMsalError}` : ". Verifica tu conexión."));
            return;
        }
    }

    setLoading(true, "Esperando autenticación de Microsoft...");

    try {
        const loginResponse = await msalInstance.loginPopup({
            scopes: ["User.Read", "openid", "profile", "email"]
        });

        const token = loginResponse.idToken || loginResponse.accessToken;

        setLoading(true, "Validando credenciales institucionales...");

        const meResponse = await fetch("/api/v1/auth/me", {
            method: "GET",
            headers: {
                "Authorization": "Bearer " + token,
                "Accept":        "application/json"
            }
        });

        if (meResponse.ok) {
            const userData = await meResponse.json();

            // Guardar en sessionStorage y cookie
            sessionStorage.setItem("plurione_auth_token", token);
            document.cookie = `plurione_auth_token=${encodeURIComponent(token)}; path=/; max-age=86400; SameSite=Lax`;

            // Registrar sesión en backend
            fetch("/api/v1/auth/session", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token: token })
            }).catch(() => {});

            const nombreUsuario = userData.name || "Usuario Institucional";
            showSuccess(`Bienvenido, ${nombreUsuario}. Redirigiendo al portal...`);

            setTimeout(() => {
                window.location.href = "/api/v1/app/dashboard";
            }, 800);

        } else {
            const errData = await meResponse.json().catch(() => ({}));
            const detail  = errData.detail ||
                "Su cuenta institucional no tiene roles asignados en el sistema de PluriOne. " +
                "Contacte al Administrador para que le asigne los permisos correspondientes.";
            showError(detail);
            setLoading(false);
        }

    } catch (err) {
        console.error("[PluriOne Auth] Error durante el login:", err);
        setLoading(false);

        if (err?.errorCode === "user_cancelled" || err?.message?.includes("user_cancelled")) {
            showError("El inicio de sesión fue cancelado.");
        } else if (err?.errorCode === "popup_window_error") {
            showError(
                "La ventana emergente de Microsoft fue bloqueada. " +
                "Por favor habilite las ventanas emergentes para este sitio en su navegador."
            );
        } else if (err?.message?.includes("NetworkError") || err?.message?.includes("Failed to fetch")) {
            showError("Error de red. Verifique su conexión a internet e intente nuevamente.");
        } else {
            showError(
                "No fue posible completar la autenticación con Microsoft Entra ID. " +
                (err?.message ? `(${err.message})` : "Si el problema persiste, contacte al soporte técnico.")
            );
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ACCESO EN MODO DESARROLLO (SIMULADOR RBAC)
// ─────────────────────────────────────────────────────────────────────────────

async function executeDevLogin() {
    hideAlerts();
    const roleSelect = document.getElementById("dev-role-select");
    const rol = roleSelect ? roleSelect.value : "REVISOR_JURIDICO";
    const roleNames = {
        "REVISOR_JURIDICO": "Abogado Revisor",
        "APROBADOR_JURIDICO": "Aprobador Jurídico",
        "ADMINISTRADOR_PLATAFORMA": "Administrador Local",
        "AUDITOR": "Auditor Interno"
    };
    const correo = `${rol.toLowerCase()}@local.dev`;
    const nombre = roleNames[rol] || "Usuario Desarrollo";

    const devBtn = document.getElementById("btn-dev-login");
    if (devBtn) {
        devBtn.disabled = true;
        devBtn.innerHTML = "<span>Accediendo...</span>";
    }

    try {
        const res = await fetch("/api/v1/auth/dev-login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rol: rol, correo: correo, nombre: nombre })
        });
        if (res.ok) {
            const data = await res.json();
            sessionStorage.setItem("plurione_auth_token", data.token);
            showSuccess(`Sesión iniciada como ${data.name}. Redirigiendo...`);
            setTimeout(() => {
                window.location.href = "/api/v1/app/dashboard";
            }, 600);
        } else {
            const err = await res.json().catch(() => ({}));
            showError(err.detail || "Error al iniciar sesión en modo desarrollo.");
            if (devBtn) {
                devBtn.disabled = false;
                devBtn.innerHTML = "<span>Ingresar en Modo Desarrollo</span>";
            }
        }
    } catch (e) {
        showError("No se pudo conectar con el endpoint de dev-login.");
        if (devBtn) {
            devBtn.disabled = false;
            devBtn.innerHTML = "<span>Ingresar en Modo Desarrollo</span>";
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// EXPOSICIÓN GLOBAL Y EVENT LISTENERS (100% COMPATIBLES CON CSP STRICT)
// ─────────────────────────────────────────────────────────────────────────────

window.loginWithMicrosoft = loginWithMicrosoft;
window.executeDevLogin = executeDevLogin;

function bindEventListeners() {
    const btn = document.getElementById("btn-login");
    if (btn) {
        btn.disabled = false;
        btn.addEventListener("click", loginWithMicrosoft);
    }
    const devBtn = document.getElementById("btn-dev-login");
    if (devBtn) {
        devBtn.addEventListener("click", executeDevLogin);
    }
}

function start() {
    bindEventListeners();
    initAuth();
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
} else {
    start();
}

