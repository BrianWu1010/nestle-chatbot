import { Helmet } from "react-helmet-async";

import { assistantConfig } from "../../assistantConfig";
import { ChatWidget } from "../../components/ChatWidget";
import styles from "./Home.module.css";

const BRANDS = ["KIT KAT", "SMARTIES", "AERO", "COFFEE CRISP", "MAGGI", "NESCAFÉ", "HÄAGEN-DAZS", "DRUMSTICK", "BOOST", "CARNATION"];

const IDEAS = [
    { title: "Recipes", text: "Find recipes that use your favourite Nestlé products, from SMARTIES cookies to MAGGI curries." },
    { title: "Products", text: "Ask about sizes, flavours, nutrition and ingredients across Made with Nestlé brands." },
    { title: "Allergens", text: "Check which products contain or may contain peanuts, tree nuts, milk, wheat and more." }
];

const Home = () => (
    <div
        className={styles.page}
        style={{ "--assistant-primary": assistantConfig.primaryColor, "--assistant-accent": assistantConfig.accentColor } as React.CSSProperties}
    >
        <Helmet>
            <title>{`${assistantConfig.name} | Made with Nestlé`}</title>
        </Helmet>
        <header className={styles.topBar}>
            <span className={styles.wordmark}>Made with Nestlé</span>
            <a className={styles.topLink} href="#/chat">
                Full-page chat
            </a>
        </header>

        <main className={styles.hero}>
            <div className={styles.heroText}>
                <p className={styles.eyebrow}>Meet {assistantConfig.name}</p>
                <h1 className={styles.heroTitle}>Good food, good questions.</h1>
                <p className={styles.heroSubtitle}>
                    {assistantConfig.tagline}. Answers come straight from madewithnestle.ca, with a source link for every fact.
                </p>
                <ul className={styles.brandList} aria-label="Brands">
                    {BRANDS.map(brand => (
                        <li key={brand} className={styles.brandChip}>
                            {brand}
                        </li>
                    ))}
                </ul>
            </div>
            <ul className={styles.ideaList}>
                {IDEAS.map(idea => (
                    <li key={idea.title} className={styles.ideaCard}>
                        <h2>{idea.title}</h2>
                        <p>{idea.text}</p>
                    </li>
                ))}
            </ul>
        </main>

        <footer className={styles.footer}>
            Demo assistant built on public Made with Nestlé content. Not affiliated with or endorsed by Nestlé. Always check product labels for allergens.
        </footer>

        <ChatWidget />
    </div>
);

export default Home;
