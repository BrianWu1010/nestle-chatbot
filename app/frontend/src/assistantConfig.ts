import defaultIcon from "./assets/assistant-icon.svg";

export interface AssistantConfig {
    name: string;
    tagline: string;
    iconUrl: string;
    primaryColor: string;
    accentColor: string;
}

// Override any of these at build time, e.g. VITE_ASSISTANT_NAME="Choco" npm run build
const env = import.meta.env;

export const assistantConfig: AssistantConfig = {
    name: env.VITE_ASSISTANT_NAME || "Nessie",
    tagline: env.VITE_ASSISTANT_TAGLINE || "Your Made with Nestlé recipe & product guide",
    iconUrl: env.VITE_ASSISTANT_ICON_URL || defaultIcon,
    primaryColor: env.VITE_ASSISTANT_PRIMARY_COLOR || "#5b3a29",
    accentColor: env.VITE_ASSISTANT_ACCENT_COLOR || "#d52b1e"
};
