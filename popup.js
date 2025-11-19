document.addEventListener('DOMContentLoaded', () => {
    const domainValue = document.getElementById('domainValue');
    const typeValue = document.getElementById('typeValue');
    const ipValue = document.getElementById('ipValue');
    const addRuleBtn = document.getElementById('addRuleBtn');
    const resultContainer = document.getElementById('resultContainer');
    const statusContainer = document.getElementById('statusContainer');
    const message = document.getElementById('message');

    // Get current tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs || tabs.length === 0) {
            showError("No active tab found");
            return;
        }

        const url = tabs[0].url;
        let domain;
        try {
            domain = new URL(url).hostname;
            domainValue.innerText = domain;
        } catch (e) {
            domainValue.innerText = "Invalid URL";
            showError("Cannot parse domain");
            return;
        }

        // Request IP from background
        chrome.runtime.sendMessage({ action: "getIp", url }, (response) => {
            statusContainer.classList.add('hidden');

            if (chrome.runtime.lastError) {
                showError("Extension error: " + chrome.runtime.lastError.message);
                return;
            }

            if (response && response.value) {
                // Success
                resultContainer.classList.remove('hidden');
                typeValue.innerText = response.type;
                ipValue.innerText = response.value;

                addRuleBtn.disabled = false;
                addRuleBtn.innerText = "Add Rule to TunnelTo";

                // Check if rule exists
                chrome.runtime.sendNativeMessage('com.tunnel.rule',
                    { action: "checkRule", ip: response.value },
                    function (nativeResponse) {
                        if (chrome.runtime.lastError) {
                            console.log("Native host not found or error");
                            return;
                        }
                        if (nativeResponse && nativeResponse.exists) {
                            addRuleBtn.innerText = "Rule Already Exists (Re-add)";
                            addRuleBtn.classList.add('exists');
                            showMessage("Rule already exists for " + nativeResponse.rule.name);
                        }
                    }
                );

                addRuleBtn.onclick = () => {
                    // 1. Copy to clipboard as backup
                    navigator.clipboard.writeText(response.value);

                    // 2. Send to Native Host
                    statusContainer.classList.remove('hidden');
                    statusContainer.innerHTML = '<div class="loader"></div><span class="status-text">Adding rule...</span>';

                    chrome.runtime.sendNativeMessage('com.tunnel.rule',
                        {
                            action: "addRule",
                            domain: domain,
                            ip: response.value,
                            type: response.type
                        },
                        function (nativeResponse) {
                            if (chrome.runtime.lastError) {
                                showError("Native Host Error: " + chrome.runtime.lastError.message);
                                // Fallback message
                                setTimeout(() => showMessage("Copied to clipboard (Host not found)"), 1000);
                                return;
                            }

                            if (nativeResponse && nativeResponse.status === "success") {
                                showMessage(nativeResponse.message);
                                statusContainer.classList.add('hidden');
                            } else {
                                showError("Error: " + (nativeResponse ? nativeResponse.message : "Unknown"));
                            }
                        }
                    );
                };
            } else {
                // Error or no IP
                const errorMsg = response.error || "IP not found";
                showError(errorMsg);
            }
        });
    });

    function showError(msg) {
        statusContainer.classList.remove('hidden');
        statusContainer.innerHTML = `<span class="error-text">${msg}</span>`;
        // Don't disable button if it's a host error, maybe user wants to copy?
        // But here we are in init phase.
        if (msg.includes("IP not found")) {
            addRuleBtn.disabled = true;
        }
    }

    function showMessage(text) {
        message.innerText = text;
        message.classList.remove('hidden');
        // Hide after 3s
        setTimeout(() => {
            message.classList.add('hidden');
        }, 3000);
    }
});
