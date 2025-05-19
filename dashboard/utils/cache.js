const CACHE_EXPIRATION_MS = 10 * 60 * 1000; // 10 minutes

export const getCachedData = (key) => {
  if (typeof window === 'undefined') return null;
  const cachedItem = localStorage.getItem(key);
  if (!cachedItem) return null;

  try {
    const { data, timestamp } = JSON.parse(cachedItem);
    if (Date.now() - timestamp > CACHE_EXPIRATION_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return data;
  } catch (error) {
    console.error("Error parsing cached data:", error);
    localStorage.removeItem(key);
    return null;
  }
};

export const setCachedData = (key, data) => {
  if (typeof window === 'undefined') return;
  try {
    const itemToCache = {
      data,
      timestamp: Date.now(),
    };
    localStorage.setItem(key, JSON.stringify(itemToCache));
  } catch (error) {
    console.error("Error setting cached data:", error);
    // Potentially handle quota exceeded error
  }
};

export const clearCache = (key) => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(key);
};

export const clearAllCache = () => {
  if (typeof window === 'undefined') return;
  localStorage.clear();
};