// Eth-Hunter Dashboard Client with Hunter Wallet Integration
const ETH_PRICE_USD = 1920.0;

const totalUsdEl = document.getElementById('total-usd');
const ethBalanceEl = document.getElementById('eth-balance');
const targetUsdEl = document.getElementById('target-usd');
const targetEthEl = document.getElementById('target-eth');
const progressBarEl = document.getElementById('progress-bar');
const progressPercentEl = document.getElementById('progress-percent');
const findingsCountEl = document.getElementById('findings-count');
const txCountEl = document.getElementById('tx-count');
const goalStatusBadgeEl = document.getElementById('goal-status-badge');
const connectionStatusEl = document.getElementById('connection-status');
const findingsListEl = document.getElementById('findings-list');
const transactionsListEl = document.getElementById('transactions-list');
const reportsListEl = document.getElementById('reports-list');
const terminalLogsEl = document.getElementById('terminal-logs');
const leaderboardCountEl = document.getElementById('leaderboard-count');
const reportsCountEl = document.getElementById('reports-count');

const walletPillEl = document.getElementById('wallet-pill');
const walletAddressShortEl = document.getElementById('wallet-address-short');
const walletFullAddrEl = document.getElementById('wallet-full-addr');
const btnGenWalletEl = document.getElementById('btn-gen-wallet');
const toastEl = document.getElementById('toast');

const tabFindingsEl = document.getElementById('tab-findings');
const tabTransactionsEl = document.getElementById('tab-transactions');

const targetInputEl = document.getElementById('target-input');
const presetSelectEl = document.getElementById('preset-select');
const btnScanEl = document.getElementById('btn-scan');
const btnScanExamplesEl = document.getElementById('btn-scan-examples');
const btnRefreshEl = document.getElementById('btn-refresh');
const btnClearTerminalEl = document.getElementById('btn-clear-terminal');

const reportModalEl = document.getElementById('report-modal');
const modalTitleEl = document.getElementById('modal-title');
const modalCodeEl = document.getElementById('modal-code');
const marketEthPriceEl = document.getElementById('market-eth-price');
const marketGasEl = document.getElementById('market-gas');
const marketBlockEl = document.getElementById('market-block');

let liveEthPrice = 1920.0;

function showToast(msg) {
  if (!toastEl) {
    console.log("Toast:", msg);
    return;
  }
  toastEl.innerText = msg;
  toastEl.style.display = 'block';
  toastEl.style.opacity = 1;
  setTimeout(() => {
    toastEl.style.opacity = 0;
    setTimeout(() => toastEl.style.display = 'none', 300);
  }, 3000);
}

async function fetchMarketData() {
  try {
    const res = await fetch('/api/market');
    if (!res.ok) return;
    const data = await res.json();
    if (data.eth_usd) {
      liveEthPrice = data.eth_usd;
      if (marketEthPriceEl) marketEthPriceEl.innerText = `ETH: $${liveEthPrice.toLocaleString()}`;
    }
    if (data.gas_gwei && marketGasEl) {
      marketGasEl.innerText = `${data.gas_gwei} Gwei`;
    }
    if (data.block_number && marketBlockEl) {
      marketBlockEl.innerText = `#${data.block_number.toLocaleString()}`;
    }
  } catch (e) {
    console.warn('Market fetch error:', e);
  }
}

const etherscanLinkEl = document.getElementById('etherscan-link');
const onchainEthValEl = document.getElementById('onchain-eth-val');
const onchainUsdValEl = document.getElementById('onchain-usd-val');
const chipsContainerEl = document.getElementById('chips-container');

// Target Registry Chips Loader
async function fetchTargets() {
  if (!chipsContainerEl) return;
  try {
    const res = await fetch('/api/targets');
    const data = await res.json();
    const targets = data.curated_targets || [];
    chipsContainerEl.innerHTML = '';
    targets.forEach(t => {
      const chip = document.createElement('button');
      chip.className = 'target-chip';
      chip.innerText = `${t.name} (${t.platform})`;
      chip.title = `${t.category} (Chain ${t.chain_id || 1}): ${t.description}`;
      chip.addEventListener('click', () => {
        targetInputEl.value = t.address || t.path;
        if (chainSelectEl && t.chain_id) chainSelectEl.value = String(t.chain_id);
        if (presetSelectEl && t.platform) presetSelectEl.value = t.platform.toLowerCase();
        showToast(`Loaded target: ${t.name}`);
      });
      chipsContainerEl.appendChild(chip);
    });
  } catch (e) {
    console.warn('Targets load failed:', e);
  }
}

// Wallet & Metrics Loader
async function fetchWalletAndMetrics() {
  try {
    const res = await fetch('/api/wallet');
    const wallet = await res.json();

    currentWalletAddress = wallet.address || "0x0000000000000000000000000000000000000000";
    const shortAddr = currentWalletAddress.slice(0, 6) + "..." + currentWalletAddress.slice(-4);
    walletAddressShortEl.innerText = shortAddr;
    walletFullAddrEl.innerText = currentWalletAddress;

    if (etherscanLinkEl) {
      etherscanLinkEl.href = `https://etherscan.io/address/${currentWalletAddress}`;
    }

    // Live On-Chain Data (Etherscan API)
    if (wallet.onchain && wallet.onchain.success) {
      const onchainEth = wallet.onchain.eth || 0;
      const onchainUsd = wallet.onchain.usd || 0;
      if (onchainEthValEl) onchainEthValEl.innerText = `${onchainEth.toFixed(6)} ETH`;
      if (onchainUsdValEl) onchainUsdValEl.innerText = `($${onchainUsd.toLocaleString()} USD)`;
    } else if (onchainEthValEl) {
      onchainEthValEl.innerText = `0.000000 ETH`;
      if (onchainUsdValEl) onchainUsdValEl.innerText = `($0.00 USD - Ready)`;
    }

    const balanceUsd = wallet.balance_usd || 0;
    const balanceEth = (wallet.balance_eth || (balanceUsd / ETH_PRICE_USD)).toFixed(3);
    const targetUsd = wallet.goal_target_usd || 2088;
    const targetEth = (wallet.goal_target_eth || (targetUsd / ETH_PRICE_USD)).toFixed(3);
    const percent = wallet.goal_progress_percent || 0;

    totalUsdEl.innerText = `$${balanceUsd.toLocaleString()}`;
    ethBalanceEl.innerText = `(${balanceEth} ETH)`;
    targetUsdEl.innerText = `Target: $${targetUsd.toLocaleString()}`;
    targetEthEl.innerText = `(${targetEth} ETH)`;

    progressBarEl.style.width = `${percent}%`;
    progressPercentEl.innerText = `${percent}% Completed`;

    if (wallet.goal_hit || balanceUsd >= targetUsd) {
      goalStatusBadgeEl.innerText = '⚡ AUTO-CLAIM ON';
      goalStatusBadgeEl.classList.add('hit');
    } else {
      goalStatusBadgeEl.innerText = 'IN PROGRESS';
      goalStatusBadgeEl.classList.remove('hit');
    }

    renderTransactions(wallet.transactions || []);
  } catch (err) {
    console.error('Failed to fetch wallet:', err);
  }
}

function renderTransactions(txs) {
  txCountEl.innerText = `${txs.length} Bounty Payouts Credited`;

  if (txs.length === 0) {
    transactionsListEl.innerHTML = '<div class="empty-state">No payout transactions recorded yet. Run an audit to claim bounty rewards!</div>';
    return;
  }

  transactionsListEl.innerHTML = txs.map(tx => `
    <div class="tx-item">
      <div class="tx-header">
        <span class="tx-platform">${tx.platform || 'Immunefi'}</span>
        <span class="tx-amount">+$${(tx.amount_usd || 0).toLocaleString()} (${tx.amount_eth || 0} ETH)</span>
      </div>
      <div class="finding-title">${tx.finding}</div>
      <div class="tx-hash">TX: ${tx.tx_hash ? tx.tx_hash.slice(0, 18) + '...' + tx.tx_hash.slice(-8) : '0x000...'}</div>
      <div class="tx-footer">
        <span>Status: <b style="color: var(--accent-green)">${tx.status || 'CONFIRMED'}</b></span>
        <span>${tx.timestamp}</span>
      </div>
    </div>
  `).join('');
}

// Fetch Leaderboard
async function fetchLeaderboard() {
  try {
    const res = await fetch('/api/leaderboard');
    const data = await res.json();
    renderFindings(data.findings || []);
  } catch (err) {
    console.error('Failed to fetch leaderboard:', err);
  }
}

function renderFindings(findings) {
  leaderboardCountEl.innerText = findings.length;
  findingsCountEl.innerText = `${findings.length} Verified Findings`;

  if (findings.length === 0) {
    findingsListEl.innerHTML = '<div class="empty-state">No findings recorded yet. Run an audit to populate the leaderboard.</div>';
    return;
  }

  findingsListEl.innerHTML = findings.map(f => `
    <div class="finding-item">
      <div class="finding-header">
        <span class="severity-pill severity-${f.severity}">${f.severity}</span>
        <span class="finding-bounty">$${(f.bounty_estimate || 0).toLocaleString()}</span>
      </div>
      <div class="finding-title">${f.finding}</div>
      <div class="finding-footer">
        <span>Target: ${f.repo}</span>
        <span>Conf: ${f.confidence}% (Score: ${f.score})</span>
      </div>
    </div>
  `).reverse().join('');
}

// Fetch Reports
async function fetchReports() {
  try {
    const res = await fetch('/api/reports');
    const reports = await res.json();
    reportsCountEl.innerText = reports.length;

    if (reports.length === 0) {
      reportsListEl.innerHTML = '<div class="empty-state">No reports generated yet.</div>';
      return;
    }

    reportsListEl.innerHTML = reports.map(r => `
      <div class="report-item" onclick="viewReport('${r.filename}')">
        <div class="report-name">📄 ${r.filename}</div>
        <div class="report-meta">
          <span>${(r.size / 1024).toFixed(1)} KB</span>
          <span>Click to Preview</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to fetch reports:', err);
  }
}

async function viewReport(filename) {
  try {
    const res = await fetch(`/api/reports/${filename}`);
    const data = await res.json();
    modalTitleEl.innerText = filename;
    modalCodeEl.innerText = data.content;
    reportModalEl.classList.add('active');
  } catch (err) {
    alert('Failed to load report: ' + err);
  }
}

// Log Polling
async function pollLogs() {
  try {
    const res = await fetch('/api/logs');
    if (!res.ok) return;
    const data = await res.json();
    const logs = data.logs || [];
    
    if (logs.length !== lastLogCount) {
      terminalLogsEl.innerHTML = '';
      logs.forEach(line => {
        const lineEl = document.createElement('div');
        lineEl.className = 'terminal-line';
        if (line.includes('🏆') || line.includes('🎉') || line.includes('🟢') || line.includes('💼')) {
          lineEl.classList.add('system');
        }
        lineEl.innerText = line;
        terminalLogsEl.appendChild(lineEl);
      });
      terminalLogsEl.scrollTop = terminalLogsEl.scrollHeight;
      lastLogCount = logs.length;
    }
    connectionStatusEl.innerText = 'Connected (Engine Active)';
  } catch (err) {
    connectionStatusEl.innerText = 'Connecting...';
  }
}

// Tab Switching
const tabDedupEl = document.getElementById('tab-dedup');
const dedupListEl = document.getElementById('dedup-list');
const dedupSearchInputEl = document.getElementById('dedup-search-input');
const dedupItemsContainerEl = document.getElementById('dedup-items-container');

let allDedupClusters = [];

async function loadDeduplicatedFindings() {
  if (!dedupItemsContainerEl) return;
  try {
    const res = await fetch('/api/deduplicated_findings');
    const data = await res.json();
    allDedupClusters = data.clusters || [];
    renderDedupClusters(allDedupClusters);
  } catch (e) {
    dedupItemsContainerEl.innerHTML = `<div class="empty-state">Failed to load findings: ${e.message}</div>`;
  }
}

function renderDedupClusters(clusters) {
  if (!dedupItemsContainerEl) return;
  if (!clusters.length) {
    dedupItemsContainerEl.innerHTML = '<div class="empty-state">No matching vulnerability archetypes found.</div>';
    return;
  }
  dedupItemsContainerEl.innerHTML = '';
  clusters.forEach(c => {
    const card = document.createElement('div');
    card.className = 'finding-item';
    card.style.cursor = 'pointer';
    const sevClass = (c.severity || 'medium').toLowerCase();
    const sevBadge = c.severity === 'Critical' ? '🚨 CRITICAL' : (c.severity === 'High' ? '🔴 HIGH' : '🟡 MEDIUM');
    
    card.innerHTML = `
      <div class="finding-header" style="display: flex; justify-content: space-between; align-items: center;">
        <span class="finding-id" style="font-weight: 700; color: var(--accent-cyan); font-family: monospace;">${c.cluster_id}</span>
        <span class="severity-badge ${sevClass}">${sevBadge}</span>
      </div>
      <div class="finding-title" style="font-weight: 600; margin: 4px 0; color: #fff;">${c.title}</div>
      <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 6px;">Target: <code style="color: #a0aec0;">${c.target}</code> (${c.occurrence_count}x detected)</div>
      <div style="display: flex; justify-content: space-between; font-size: 12px;">
        <span style="color: var(--accent-green); font-weight: 600;">+$${Number(c.unit_bounty_usd || 0).toLocaleString()} USD</span>
        <span style="color: var(--accent-blue); font-size: 11px; text-decoration: underline;">📄 View Submission</span>
      </div>
    `;

    card.addEventListener('click', () => {
      viewBatchSubmission(c);
    });

    dedupItemsContainerEl.appendChild(card);
  });
}

async function viewBatchSubmission(c) {
  const safeTarget = c.target.replace(/\//g, '_').replace('.sol', '');
  const fname = `${c.cluster_id}_${c.severity.toUpperCase()}_${safeTarget}.md`;
  try {
    const res = await fetch(`/api/submissions/batch/${encodeURIComponent(fname)}`);
    if (res.ok) {
      const data = await res.json();
      modalTitleEl.innerText = `[${c.severity.toUpperCase()}] ${c.title}`;
      modalCodeEl.innerText = data.content;
      reportModalEl.classList.add('active');
      return;
    }
  } catch (e) {}

  // Fallback to sample report
  if (c.sample_report) {
    const rName = c.sample_report.split('/').pop();
    viewReport(rName);
  }
}

if (dedupSearchInputEl) {
  dedupSearchInputEl.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) {
      renderDedupClusters(allDedupClusters);
      return;
    }
    const filtered = allDedupClusters.filter(c => 
      c.title.toLowerCase().includes(q) ||
      c.target.toLowerCase().includes(q) ||
      c.severity.toLowerCase().includes(q) ||
      (c.threat_class && c.threat_class.toLowerCase().includes(q))
    );
    renderDedupClusters(filtered);
  });
}

tabFindingsEl.addEventListener('click', () => {
  tabFindingsEl.classList.add('active');
  tabTransactionsEl.classList.remove('active');
  if (tabDedupEl) tabDedupEl.classList.remove('active');
  findingsListEl.style.display = 'block';
  transactionsListEl.style.display = 'none';
  if (dedupListEl) dedupListEl.style.display = 'none';
});

tabTransactionsEl.addEventListener('click', () => {
  tabTransactionsEl.classList.add('active');
  tabFindingsEl.classList.remove('active');
  if (tabDedupEl) tabDedupEl.classList.remove('active');
  findingsListEl.style.display = 'none';
  transactionsListEl.style.display = 'block';
  if (dedupListEl) dedupListEl.style.display = 'none';
});

if (tabDedupEl) {
  tabDedupEl.addEventListener('click', () => {
    tabDedupEl.classList.add('active');
    tabFindingsEl.classList.remove('active');
    tabTransactionsEl.classList.remove('active');
    findingsListEl.style.display = 'none';
    transactionsListEl.style.display = 'none';
    if (dedupListEl) dedupListEl.style.display = 'block';
    loadDeduplicatedFindings();
  });
}

// Copy Wallet Address
walletPillEl.addEventListener('click', () => {
  if (currentWalletAddress) {
    navigator.clipboard.writeText(currentWalletAddress).then(() => {
      showToast('Wallet address copied: ' + currentWalletAddress);
    }).catch(() => {
      showToast('Address: ' + currentWalletAddress);
    });
  }
});

// Auto-Claim All Payouts
const btnAutoClaimEl = document.getElementById('btn-auto-claim');
const btnSetCustomAddrEl = document.getElementById('btn-set-custom-addr');
const btnCheckOnchainEl = document.getElementById('btn-check-onchain');

if (btnAutoClaimEl) {
  btnAutoClaimEl.addEventListener('click', async () => {
    btnAutoClaimEl.disabled = true;
    btnAutoClaimEl.innerText = 'Claiming...';
    try {
      const res = await fetch('/api/wallet/claim_all', { method: 'POST' });
      const data = await res.json();
      fetchWalletAndMetrics();
      showToast(`🎉 Auto-Claimed ${data.claimed_count} payouts!`);
    } catch (err) {
      alert('Auto-claim failed: ' + err);
    } finally {
      btnAutoClaimEl.disabled = false;
      btnAutoClaimEl.innerText = '💰 Auto-Claim All';
    }
  });
}

if (btnSetCustomAddrEl) {
  btnSetCustomAddrEl.addEventListener('click', async () => {
    const input = prompt('Enter your Ethereum wallet address (0x...):', currentWalletAddress);
    if (!input) return;
    const addr = input.trim();
    if (!addr.startsWith('0x') || addr.length !== 42) {
      return alert('Invalid Ethereum address. Must start with 0x and be 42 characters long.');
    }
    try {
      const res = await fetch('/api/wallet/set_address', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      fetchWalletAndMetrics();
      showToast('Custom address set: ' + addr.slice(0, 8) + '...');
    } catch (err) {
      alert('Failed to set address: ' + err.message);
    }
  });
}

const btnSetApiKeyEl = document.getElementById('btn-set-api-key');

if (btnSetApiKeyEl) {
  btnSetApiKeyEl.addEventListener('click', async () => {
    const key = prompt('Enter your Etherscan API Key (leave empty to use free public RPC nodes):');
    if (key === null) return;
    try {
      const res = await fetch('/api/settings/etherscan_key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: key.trim() })
      });
      const data = await res.json();
      if (data.success) {
        showToast('🔑 Etherscan API Key updated!');
      } else {
        alert('Failed to save key: ' + (data.error || 'Unknown error'));
      }
    } catch (e) {
      alert('Request error: ' + e);
    }
  });
}

if (btnCheckOnchainEl) {
  btnCheckOnchainEl.addEventListener('click', async () => {
    btnCheckOnchainEl.innerText = 'Checking...';
    try {
      const chainId = chainSelectEl ? chainSelectEl.value : "1";
      const res = await fetch(`/api/etherscan/balance?address=${currentWalletAddress}&chain_id=${chainId}`);
      const data = await res.json();
      if (data.success) {
        showToast(`${data.chain_name || 'Network'} Balance: ${data.eth} ${data.symbol || 'ETH'}`);
        alert(`🌐 Live On-Chain Balance:\n\nSource: ${data.source}\nNetwork: ${data.chain_name} (Chain ID: ${data.chain_id})\nAddress: ${data.address}\nBalance: ${data.eth} ${data.symbol || 'ETH'} ($${data.usd.toLocaleString()} USD)\nWei: ${data.wei}`);
      } else {
        alert(`On-Chain Query Note (${data.chain_name || 'Chain'}): ${data.error || 'No live on-chain balance returned'}`);
      }
    } catch (err) {
      alert('On-chain request failed: ' + err);
    } finally {
      btnCheckOnchainEl.innerText = '🌐 Check On-Chain';
    }
  });
}

// Generate New Wallet
btnGenWalletEl.addEventListener('click', async () => {
  if (!confirm('Generate a new random Ethereum Hunter Wallet address?')) return;
  try {
    const res = await fetch('/api/wallet/generate', { method: 'POST' });
    if (!res.ok) {
      const errTxt = await res.text();
      throw new Error(errTxt || `Server returned ${res.status}`);
    }
    const data = await res.json();
    fetchWalletAndMetrics();
    showToast('🎲 New wallet generated: ' + (data.address ? data.address.slice(0, 8) + '...' : ''));
  } catch (err) {
    alert('Failed to generate wallet: ' + err.message);
  }
});

const chainSelectEl = document.getElementById('chain-select');

// Audit Actions
btnScanEl.addEventListener('click', async () => {
  const target = targetInputEl.value.trim();
  const preset = presetSelectEl.value;
  const chainId = chainSelectEl ? parseInt(chainSelectEl.value) : 1;
  if (!target) return alert('Please enter a target path or repository URL.');

  btnScanEl.disabled = true;
  btnScanEl.innerText = 'Scanning...';
  try {
    await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, preset, provider: 'mock', chain_id: chainId })
    });
  } catch (err) {
    alert('Scan dispatch failed: ' + err);
  } finally {
    setTimeout(() => {
      btnScanEl.disabled = false;
      btnScanEl.innerText = '⚡ RUN AUDIT';
      fetchWalletAndMetrics();
      fetchLeaderboard();
      fetchReports();
    }, 2500);
  }
});

const btnBlockscanEl = document.getElementById('btn-blockscan');

if (btnBlockscanEl) {
  btnBlockscanEl.addEventListener('click', () => {
    let target = targetInputEl.value.trim();
    let addrMatch = target.match(/0x[a-fA-F0-9]{40}/);
    let address = addrMatch ? addrMatch[0] : (currentWalletAddress || "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45");
    const chainId = chainSelectEl ? chainSelectEl.value : "1";
    const blockscanUrl = `https://vscode.blockscan.com/${chainId}/${address}`;
    window.open(blockscanUrl, '_blank');
    showToast(`Opening Blockscan (Chain ${chainId}) for ${address.slice(0, 8)}...`);
  });
}

btnScanExamplesEl.addEventListener('click', () => {
  targetInputEl.value = 'examples/sample_vulnerable_vault.sol';
  btnScanEl.click();
});

btnRefreshEl.addEventListener('click', () => {
  fetchTargets();
  fetchWalletAndMetrics();
  fetchLeaderboard();
  fetchReports();
  pollLogs();
  showToast('Dashboard refreshed');
});

btnClearTerminalEl.addEventListener('click', () => {
  terminalLogsEl.innerHTML = '<div class="terminal-line system">[SYSTEM] Terminal cleared.</div>';
});

btnCloseModalEl.addEventListener('click', () => {
  reportModalEl.classList.remove('active');
});

// Initial load & interval loops
fetchTargets();
fetchMarketData();
fetchWalletAndMetrics();
fetchLeaderboard();
fetchReports();
pollLogs();

setInterval(() => {
  fetchMarketData();
  fetchWalletAndMetrics();
  fetchLeaderboard();
  fetchReports();
  pollLogs();
}, 2500);
