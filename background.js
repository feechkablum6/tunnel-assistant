function getDomain(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

async function fetchIp(domain) {
  try {
    // Try IPv4 first
    const dnsApi = `https://dns.google/resolve?name=${domain}&type=A`;
    const res = await fetch(dnsApi);
    const json = await res.json();
    if (json.Answer && json.Answer.length > 0) {
      // Filter for type 1 (A record) just in case
      const aRecord = json.Answer.find(rec => rec.type === 1);
      if (aRecord) {
        return {type: "IPv4 Address", value: aRecord.data};
      }
    }

    // Try IPv6 if no IPv4 found (or just check both, but usually we want one primary)
    // The user logic implies checking IPv6 if IPv4 is found? Or just finding *an* IP.
    // Let's check IPv6 as fallback or alternative.
    const dnsApi6 = `https://dns.google/resolve?name=${domain}&type=AAAA`;
    const res6 = await fetch(dnsApi6);
    const json6 = await res6.json();
    if (json6.Answer && json6.Answer.length > 0) {
       const aaaaRecord = json6.Answer.find(rec => rec.type === 28);
       if (aaaaRecord) {
         return {type: "IPv6 Address", value: aaaaRecord.data};
       }
    }
    
    return { error: "IP not found" };
  } catch (e) {
    console.error("DNS Fetch error:", e);
    return { error: "DNS Lookup failed" };
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "getIp") {
    const domain = getDomain(msg.url);
    if (!domain) {
      sendResponse({ error: "Invalid URL" });
      return true;
    }
    
    fetchIp(domain).then(data => sendResponse(data));
    return true; // Keep channel open for async response
  }
});
