import SignInPage from "./auth/SignInPage";
import { useSession } from "./auth/useSession";
import { useHashRoute } from "./app/useHashRoute";
import CreateDealPage from "./deals/CreateDealPage";
import DealDetailPage from "./deals/DealDetailPage";
import DealsPage from "./deals/DealsPage";
import { navigateToCreateDeal, navigateToDeal, navigateToDeals } from "./router";

export default function App() {
  const { accessToken, signIn, signOut } = useSession();
  const route = useHashRoute();

  if (!accessToken) {
    return <SignInPage onSignIn={signIn} />;
  }

  const isCreate = route.name === "create";

  return (
    <div className="app-shell">
      <header className="site-nav">
        <button type="button" className="brand" onClick={navigateToDeals}>
          <span className="brand__mark" aria-hidden="true">
            <svg viewBox="0 0 28 28" focusable="false">
              <path d="M4 6.5h13.5L24 13v8.5H10.5L4 15z" />
              <path d="M4 6.5 10.5 13v8.5M10.5 13H24" />
            </svg>
          </span>
          <span className="brand__type">
            <span>SyncAlly</span>
            <small>TRADE FOLIO</small>
          </span>
        </button>
        <nav className="site-nav__links" aria-label="Primary">
          <button
            type="button"
            className={`nav-link${!isCreate ? " is-active" : ""}`}
            onClick={navigateToDeals}
          >
            Workspace
          </button>
          <button
            type="button"
            className={`nav-link${isCreate ? " is-active" : ""}`}
            onClick={navigateToCreateDeal}
          >
            New deal
          </button>
        </nav>
        <div className="site-nav__meta">
          <span className="site-nav__environment">LOCAL DEMO</span>
          <button type="button" className="button ghost" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>

      <main className="app-main">
        {route.name === "deal" ? (
          <DealDetailPage
            key={route.dealId}
            dealId={route.dealId}
            onBackToDeals={navigateToDeals}
          />
        ) : route.name === "create" ? (
          <CreateDealPage onCreated={navigateToDeal} />
        ) : (
          <DealsPage onOpenDeal={navigateToDeal} onCreateDeal={navigateToCreateDeal} />
        )}
      </main>

      <footer className="site-footer">
        <div className="site-footer__inner">
          <div className="site-footer__row">
            <span>SYNCALLY / SHARED TRADE RECORD</span>
            <span>Every reviewed term stays tied to its source.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
