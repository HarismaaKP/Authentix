(() => {
  const form = document.getElementById('registerForm');
  const fileInput = document.getElementById('originalImage');
  const preview = document.getElementById('previewImg');
  const dropzone = document.getElementById('dropzone');
  const errorBox = document.getElementById('registerError');
  const submitBtn = document.getElementById('registerSubmit');

  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (!file) return;
    preview.src = URL.createObjectURL(file);
    preview.style.display = 'block';
  });

  ['dragover', 'dragleave', 'drop'].forEach(evt => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.toggle('dragover', evt === 'dragover');
    });
  });
  dropzone.addEventListener('drop', (e) => {
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      fileInput.dispatchEvent(new Event('change'));
    }
  });

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.classList.add('show');
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.classList.remove('show');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Writing to the blockchain…';

    const fd = new FormData(form);

    try {
      const res = await fetch('/api/register', { method: 'POST', body: fd });
      const data = await res.json();
      if (!data.ok) {
        showError(data.error || 'Registration failed.');
        return;
      }

      document.getElementById('resultProductName').textContent = document.getElementById('name').value;
      document.getElementById('resultQr').src = data.qr_code_url;
      document.getElementById('resultProductId').textContent = data.product_id;
      document.getElementById('resultChainMode').textContent = data.chain_mode === 'web3' ? 'Live Ethereum node' : 'Local hash-chain ledger';
      document.getElementById('resultBlockIndex').textContent = data.block_index;
      document.getElementById('resultTxHash').textContent = data.tx_hash;
      document.getElementById('resultVerifyLink').href = data.verify_url;

      document.getElementById('registerCard').style.display = 'none';
      document.getElementById('resultCard').style.display = 'block';
    } catch (err) {
      showError('Could not reach the server. Please try again.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Register on the blockchain';
    }
  });

  document.getElementById('registerAnother').addEventListener('click', () => {
    form.reset();
    preview.style.display = 'none';
    document.getElementById('registerCard').style.display = 'block';
    document.getElementById('resultCard').style.display = 'none';
  });
})();
