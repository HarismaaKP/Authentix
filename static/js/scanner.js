(() => {

  const video = document.getElementById('scannerVideo');
  const hint = document.getElementById('scannerHint');
  const errorBox = document.getElementById('scanError');
  const qrUpload = document.getElementById('qrUpload');
  const manualForm = document.getElementById('manualForm');

  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d', {
    willReadFrequently: true
  });

  let streaming = false;


  // Show error message
  function showError(message) {

    errorBox.textContent = message;
    errorBox.classList.add('show');

  }


  // Go to product verification page
  function goToProduct(rawValue) {

    let productId = rawValue.trim();

    const match = productId.match(
      /\/verify\/([A-Za-z0-9\-]+)/
    );

    if (match) {
      productId = match[1];
    }

    if (!productId) {
      return;
    }

    window.location.href =
      `/verify/${encodeURIComponent(productId)}`;

  }


  // Read QR code from an image
  function readQRCode(img) {

    canvas.width = img.width;
    canvas.height = img.height;

    ctx.clearRect(
      0,
      0,
      canvas.width,
      canvas.height
    );

    ctx.drawImage(
      img,
      0,
      0,
      canvas.width,
      canvas.height
    );

    const imageData = ctx.getImageData(
      0,
      0,
      canvas.width,
      canvas.height
    );


    // Check jsQR library
    if (!window.jsQR) {

      showError(
        'QR scanner library could not be loaded.'
      );

      return;
    }


    // Decode QR
    const code = window.jsQR(
      imageData.data,
      imageData.width,
      imageData.height
    );


    if (code && code.data) {

      hint.textContent =
        'QR code detected!';

      goToProduct(code.data);

    } else {

      hint.textContent =
        'QR code could not be detected.';

      showError(
        'Could not read the QR code. Please try a clearer image.'
      );

    }

  }


  // Camera scanning
  function tick() {

    if (!streaming) {
      return;
    }

    if (
      video.readyState ===
      video.HAVE_ENOUGH_DATA
    ) {

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      ctx.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
      );

      const imageData =
        ctx.getImageData(
          0,
          0,
          canvas.width,
          canvas.height
        );


      if (window.jsQR) {

        const code = window.jsQR(
          imageData.data,
          imageData.width,
          imageData.height
        );


        if (code && code.data) {

          streaming = false;

          if (video.srcObject) {

            const tracks =
              video.srcObject.getTracks();

            tracks.forEach(
              track => track.stop()
            );

          }

          goToProduct(code.data);

          return;
        }

      }

    }

    requestAnimationFrame(tick);

  }


  // Start camera
  async function startCamera() {

    try {

      if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
      ) {

        hint.textContent =
          'Camera unavailable — use the upload option below.';

        return;
      }


      const stream =
        await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment'
          }
        });


      video.srcObject = stream;

      await video.play();

      streaming = true;

      hint.textContent =
        'Align the QR code within the frame.';

      tick();

    } catch (error) {

      console.log(
        'Camera error:',
        error
      );

      hint.textContent =
        'Camera unavailable — use the upload option below.';

    }

  }


  // =========================================================
  // UPLOAD QR IMAGE
  // =========================================================

  if (qrUpload) {

    qrUpload.addEventListener(
      'change',
      function (event) {

        const file =
          event.target.files[0];


        if (!file) {
          return;
        }


        hint.textContent =
          'Reading QR code...';


        const reader =
          new FileReader();


        reader.onload = function (event) {

          const img =
            new Image();


          img.onload = function () {

            readQRCode(img);

          };


          img.onerror = function () {

            showError(
              'Unable to open the selected image.'
            );

          };


          img.src =
            event.target.result;

        };


        reader.onerror = function () {

          showError(
            'Unable to read the selected file.'
          );

        };


        reader.readAsDataURL(file);

      }
    );

  } else {

    console.log(
      'QR upload input not found.'
    );

  }


  // =========================================================
  // MANUAL PRODUCT ID
  // =========================================================

  if (manualForm) {

    manualForm.addEventListener(
      'submit',
      function (event) {

        event.preventDefault();

        const input =
          document.getElementById('manualId');


        const value =
          input.value.trim();


        if (value) {

          goToProduct(value);

        }

      }
    );

  }


  // Start camera
  startCamera();

})();