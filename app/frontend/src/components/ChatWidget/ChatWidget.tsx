import { useEffect, useState } from "react";
import { Dismiss24Regular, Open20Regular } from "@fluentui/react-icons";

import { AssistantConfig, assistantConfig } from "../../assistantConfig";
import styles from "./ChatWidget.module.css";

interface Props {
    config?: AssistantConfig;
    /** URL of the chat page shown inside the pop-out (any page that renders the chat with ?embed=1). */
    chatUrl?: string;
    defaultOpen?: boolean;
}

export const ChatWidget = ({ config = assistantConfig, chatUrl = "#/chat?embed=1", defaultOpen = false }: Props) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);
    // Mount the iframe on first open, then keep it so the conversation survives close/reopen.
    const [hasOpened, setHasOpened] = useState(defaultOpen);

    useEffect(() => {
        if (isOpen) setHasOpened(true);
        const onKeyDown = (e: KeyboardEvent) => e.key === "Escape" && setIsOpen(false);
        window.addEventListener("keydown", onKeyDown);
        return () => window.removeEventListener("keydown", onKeyDown);
    }, [isOpen]);

    const themeVars = { "--assistant-primary": config.primaryColor, "--assistant-accent": config.accentColor } as React.CSSProperties;

    return (
        <div className={styles.root} style={themeVars}>
            {hasOpened && (
                <section className={`${styles.panel} ${isOpen ? styles.panelOpen : ""}`} aria-label={`${config.name} chat`} aria-hidden={!isOpen}>
                    <header className={styles.panelHeader}>
                        <img src={config.iconUrl} alt="" className={styles.panelIcon} />
                        <div className={styles.panelTitles}>
                            <span className={styles.panelName}>{config.name}</span>
                            <span className={styles.panelTagline}>{config.tagline}</span>
                        </div>
                        <a className={styles.headerButton} href={chatUrl.replace(/[?&]embed=1/, "")} target="_blank" rel="noreferrer" title="Open in full page">
                            <Open20Regular />
                        </a>
                        <button className={styles.headerButton} onClick={() => setIsOpen(false)} aria-label="Close chat">
                            <Dismiss24Regular />
                        </button>
                    </header>
                    <iframe className={styles.frame} src={chatUrl} title={`${config.name} chat`} />
                </section>
            )}
            <button
                className={`${styles.launcher} ${isOpen ? styles.launcherHidden : ""}`}
                onClick={() => setIsOpen(true)}
                aria-label={`Open ${config.name} chat`}
                aria-expanded={isOpen}
            >
                <img src={config.iconUrl} alt="" className={styles.launcherIcon} />
                <span className={styles.launcherLabel}>Ask {config.name}</span>
            </button>
        </div>
    );
};
