document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('footerChainStatus');
  if (!el) return;
  fetch('/api/chain-status')
    .then(r => r.json())
    .then(d => {
      const label = d.mode === 'web3' ? 'live chain' : 'local ledger';
      el.textContent = d.integrity_ok
        ? `${d.blocks} blocks · ${label} · integrity verified`
        : `integrity check failed`;
    })
    .catch(() => { el.textContent = 'ledger unreachable'; });
});
