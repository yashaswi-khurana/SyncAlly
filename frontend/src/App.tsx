import SignInPage from "./auth/SignInPage";
import { useSession } from "./auth/useSession";
import { useHashRoute } from "./app/useHashRoute";
import CreateDealPage from "./deals/CreateDealPage";
import DealDetailPage from "./deals/DealDetailPage";
import DealsPage from "./deals/DealsPage";
import { navigateToCreateDeal, navigateToDeal, navigateToDeals } from "./router";
import CustomCursor from "./ui/CustomCursor";
import LiveClock from "./ui/LiveClock";
import Marquee from "./ui/Marquee";

export default function App() {
  const { accessToken, signIn, signOut } = useSession();
  const route = useHashRoute();

  if (!accessToken) {
    return <SignInPage onSignIn={signIn} />;
  }

  const isCreate = route.name === "create";

  return (
    <div className="app-shell">
      <div className="aurora" aria-hidden="true">
        <span className="aurora__blob aurora__blob--a" />
        <span className="aurora__blob aurora__blob--b" />
      </div>
      <CustomCursor />

      <header className="site-nav">
        <button type="button" className="brand" onClick={navigateToDeals}>
          <span className="brand__mark" aria-hidden="true" />
          SyncAlly
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
          <span className="clock--optional">
            <LiveClock />
          </span>
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
          <div className="site-footer__marquee" aria-hidden="true">
            <Marquee speed={34}>
              <span>NEGOTIATE</span>
              <span>AGREE</span>
              <span>FULFIL</span>
              <span>PAY</span>
            </Marquee>
          </div>
          <p className="site-footer__cta display">Turn conversations into committed trade.</p>
          <div className="site-footer__row">
            <span>SyncAlly</span>
            <LiveClock label="LOCAL" />
          </div>
        </div>
      </footer>
    </div>
  );
}
