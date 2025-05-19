import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import dynamic from 'next/dynamic';
import '../styles/globals.css';
// import SetupWizard from '../components/SetupWizard'; // Replaced with dynamic import
// import QuickStartGuide from '../components/QuickStartGuide'; // Replaced with dynamic import
import { isFirstRun, getFirstRunStatus, markFirstRunComplete, resetFirstRunStatus } from '../utils/firstRunUtils';
import SetupNotificationBanner from '../components/SetupNotificationBanner';

const SetupWizard = dynamic(() => import('../components/SetupWizard'), {
  loading: () => <div className="flex items-center justify-center h-screen">Loading Setup...</div>,
  ssr: false,
});

const QuickStartGuide = dynamic(() => import('../components/QuickStartGuide'), {
  loading: () => <div className="flex items-center justify-center h-screen">Loading Guide...</div>,
  ssr: false,
});

function MyApp({ Component, pageProps }) {
  const [showSetupWizard, setShowSetupWizard] = useState(false);
  const [showQuickStartGuide, setShowQuickStartGuide] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showSetupBanner, setShowSetupBanner] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const firstRun = isFirstRun();
    const firstRunStatus = getFirstRunStatus();
    const needsConfig = !firstRunStatus || !firstRunStatus.completed;
    const canShowInteractiveElements = router.pathname !== '/login' && router.pathname !== '/config-wizard';

    if (isLoading) setIsLoading(false);

    if (canShowInteractiveElements) {
      if (firstRun) { // Prioritize full wizard for brand new users
        setShowSetupWizard(true);
        setShowSetupBanner(false);
        setShowQuickStartGuide(false);
      } else if (needsConfig) { // Show banner if wizard isn't active but config needed
        setShowSetupWizard(false);
        setShowSetupBanner(true);
        setShowQuickStartGuide(false);
      } else { // Configured
        setShowSetupWizard(false);
        setShowSetupBanner(false);
        // Check for quick start guide only if configured
        if (firstRunStatus?.completed && !firstRunStatus?.quickStartShown) {
          setShowQuickStartGuide(true);
          const updatedStatus = { ...firstRunStatus, quickStartShown: true };
          localStorage.setItem('cryptobot_first_run', JSON.stringify(updatedStatus));
        } else {
          setShowQuickStartGuide(false);
        }
      }
    } else { // On login or config-wizard page
      setShowSetupWizard(false);
      setShowSetupBanner(false);
      setShowQuickStartGuide(false);
    }
  }, [router.pathname, isLoading]);

  const handleSetupComplete = () => {
    markFirstRunComplete(true); // Ensure this is explicitly called
    setShowSetupWizard(false);
    setShowSetupBanner(false); // Hide banner after setup is complete
    setShowQuickStartGuide(true); // Show quick start guide
  };

  const handleBannerDismiss = () => {
    setShowSetupBanner(false);
    // Optionally, set a session flag to keep it dismissed for the session
    // sessionStorage.setItem('cryptobot_setup_banner_dismissed', 'true');
  };

  const handleQuickStartClose = () => {
    setShowQuickStartGuide(false);
  };
  
  // Reset first run status (for development/testing)
  const handleResetFirstRun = () => {
    resetFirstRunStatus();
    window.location.reload();
  };
  
  if (isLoading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }
  
  return (
    <>
      {/* Development tools - remove in production */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 z-50">
          <button
            onClick={handleResetFirstRun}
            className="bg-red-600 text-white px-3 py-1 rounded text-xs"
          >
            Reset First Run
          </button>
        </div>
      )}
      
      {/* Show setup wizard if this is the first run */}
      {showSetupWizard ? (
        <SetupWizard onComplete={handleSetupComplete} />
      ) : (
        <>
          <Component {...pageProps} />
          
          {/* Show quick start guide after setup is complete */}
          {showQuickStartGuide && (
            <QuickStartGuide onClose={handleQuickStartClose} />
          )}
          {showSetupBanner && !showSetupWizard && (
            <SetupNotificationBanner onDismiss={handleBannerDismiss} />
          )}
        </>
      )}
    </>
  );
}

export default MyApp;