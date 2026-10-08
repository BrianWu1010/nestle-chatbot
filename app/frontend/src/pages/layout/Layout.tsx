import { Outlet, Link, useSearchParams } from "react-router-dom";
import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";
import { assistantConfig } from "../../assistantConfig";

import { LoginButton } from "../../components/LoginButton";

const Layout = () => {
    const [searchParams] = useSearchParams();
    // The pop-out widget loads this page in an iframe with ?embed=1; it draws its own header.
    const embedded = searchParams.get("embed") === "1";

    return (
        <div className={styles.layout}>
            {!embedded && (
                <header className={styles.header} role={"banner"}>
                    <div className={styles.headerContainer}>
                        <Link to="/" className={styles.headerTitleContainer}>
                            <h3 className={styles.headerTitle}>{assistantConfig.name}</h3>
                        </Link>
                        <div className={styles.loginMenuContainer}>{useLogin && <LoginButton />}</div>
                    </div>
                </header>
            )}

            <main className={styles.main} id="main-content">
                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
