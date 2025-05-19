import { useState, useEffect } from 'react';
import Link from 'next/link';

export default function SetupNotificationBanner({ onDismiss }) {
  const [visible, setVisible] = useState(true);

  if (!visible) {
    return null;
  }

  const handleDismiss = () => {
    setVisible(false);
    if (onDismiss) {
      onDismiss();
    }
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-yellow-500 p-4 text-center text-black shadow-lg z-50">
      <div className="container mx-auto flex justify-between items-center">
        <span>
          It looks like your application isn't fully configured yet. Please complete the setup for the best experience.
        </span>
        <div>
          <Link href="/config-wizard" legacyBehavior>
            <a className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mr-2">
              Go to Setup
            </a>
          </Link>
          <button
            onClick={handleDismiss}
            className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded"
            aria-label="Dismiss setup notification"
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}