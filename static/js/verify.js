// (() => {
//     const lookupError = document.getElementById('lookupError');
//     const lookupLoading = document.getElementById('lookupLoading');
//     const productInfo = document.getElementById('productInfo');

//     let product = null;
//     let capturedFile = null;


//     // -----------------------------------------------------------
//     // Show error message
//     // -----------------------------------------------------------

//     function showLookupError(msg) {
//         lookupError.textContent = msg;
//         lookupError.classList.add('show');

//         if (lookupLoading) {
//             lookupLoading.style.display = 'none';
//         }
//     }


//     // -----------------------------------------------------------
//     // Load product information
//     // -----------------------------------------------------------

//     fetch(`/api/product/${encodeURIComponent(PRODUCT_ID)}`)
//         .then(response => {

//             if (!response.ok) {
//                 throw new Error("Product request failed");
//             }

//             return response.json();
//         })

//         .then(data => {

//             if (!data.ok) {

//                 showLookupError(
//                     data.error ||
//                     'This product could not be found on the ledger.'
//                 );

//                 return;
//             }

//             product = data.product;

//             document.getElementById(
//                 'originalPreview'
//             ).src = product.original_image_path;

//             document.getElementById(
//                 'infoName'
//             ).textContent = product.name;

//             document.getElementById(
//                 'infoManufacturer'
//             ).textContent = product.manufacturer;

//             document.getElementById(
//                 'infoOnChain'
//             ).textContent =
//                 data.on_chain
//                     ? 'Confirmed on ledger'
//                     : 'Not found on ledger';


//             lookupLoading.style.display = 'none';

//             productInfo.style.display = 'block';
//         })

//         .catch(error => {

//             console.error(
//                 "Product lookup error:",
//                 error
//             );

//             showLookupError(
//                 'Could not reach the server. Please try again.'
//             );
//         });


//     // -----------------------------------------------------------
//     // Image upload elements
//     // -----------------------------------------------------------

//     const capturedInput =
//         document.getElementById('capturedImage');

//     const capturedPreview =
//         document.getElementById('capturedPreview');

//     const analyzeBtn =
//         document.getElementById('analyzeBtn');


//     // -----------------------------------------------------------
//     // When customer selects an image
//     // -----------------------------------------------------------

//     capturedInput.addEventListener(
//         'change',
//         () => {

//             const file =
//                 capturedInput.files[0];

//             if (!file) {
//                 return;
//             }

//             capturedFile = file;

//             capturedPreview.src =
//                 URL.createObjectURL(file);

//             capturedPreview.style.display =
//                 'block';

//             analyzeBtn.disabled = false;
//         }
//     );


//     // -----------------------------------------------------------
//     // Analysis animation
//     // -----------------------------------------------------------

//     const stepEls =
//         Array.from(
//             document.querySelectorAll('.l-step')
//         );


//     function animateSteps() {

//         let i = 0;

//         stepEls.forEach(el => {
//             el.classList.remove(
//                 'active',
//                 'done'
//             );
//         });


//         return new Promise(resolve => {

//             const advance = () => {

//                 if (i > 0) {

//                     stepEls[
//                         i - 1
//                     ].classList.add('done');
//                 }


//                 if (i >= stepEls.length) {

//                     resolve();

//                     return;
//                 }


//                 stepEls[i].classList.add(
//                     'active'
//                 );

//                 i++;

//                 setTimeout(
//                     advance,
//                     650
//                 );
//             };


//             advance();
//         });
//     }


//     // -----------------------------------------------------------
//     // Analyze button
//     // -----------------------------------------------------------

//     analyzeBtn.addEventListener(
//         'click',
//         async () => {

//             if (!capturedFile) {

//                 showLookupError(
//                     'Please select a product image.'
//                 );

//                 return;
//             }


//             document.getElementById(
//                 'lookupCard'
//             ).style.display = 'none';

//             document.getElementById(
//                 'analyzingCard'
//             ).style.display = 'block';


//             const fd = new FormData();

//             fd.append(
//                 'captured_image',
//                 capturedFile
//             );


//             try {

//                 console.log(
//                     "Starting AI verification..."
//                 );


//                 // Start animation
//                 animateSteps();


//                 console.log(
//                     "Sending image to Flask..."
//                 );


//                 // Send image to Flask
//                 const response = await fetch(
//                     `/api/verify/${encodeURIComponent(PRODUCT_ID)}`,
//                     {
//                         method: 'POST',
//                         body: fd
//                     }
//                 );


//                 console.log(
//                     "Flask response received:",
//                     response.status
//                 );


//                 if (!response.ok) {

//                     throw new Error(
//                         `Server returned ${response.status}`
//                     );
//                 }


//                 const data =
//                     await response.json();


//                 console.log(
//                     "Verification result:",
//                     data
//                 );


//                 document.getElementById(
//                     'analyzingCard'
//                 ).style.display = 'none';


//                 if (!data.ok) {

//                     document.getElementById(
//                         'lookupCard'
//                     ).style.display = 'block';

//                     showLookupError(
//                         data.error ||
//                         'Verification failed.'
//                     );

//                     return;
//                 }


//                 // Display result
//                 renderResult(data);


//             } catch (error) {

//                 console.error(
//                     "Verification error:",
//                     error
//                 );


//                 document.getElementById(
//                     'analyzingCard'
//                 ).style.display = 'none';


//                 document.getElementById(
//                     'lookupCard'
//                 ).style.display = 'block';


//                 showLookupError(
//                     'Verification failed. Please check that Flask and MongoDB are running.'
//                 );
//             }
//         }
//     );


//     // -----------------------------------------------------------
//     // Display verification result
//     // -----------------------------------------------------------

//     function renderResult(data) {

//         const verdictClass =
//             data.verdict.toLowerCase();


//         const card =
//             document.getElementById(
//                 'resultCard'
//             );


//         document.getElementById(
//             'resultProductName'
//         ).textContent =
//             data.product_name;


//         document.getElementById(
//             'resultEyebrow'
//         ).textContent =
//             data.manufacturer;


//         const badge =
//             document.getElementById(
//                 'resultVerdictBadge'
//             );


//         const icons = {

//             authentic:
//                 '&#10003;',

//             suspicious:
//                 '&#9888;',

//             counterfeit:
//                 '&#10005;'
//         };


//         badge.innerHTML =
//             `<span class="verdict-badge ${verdictClass}">
//                 ${icons[verdictClass] || ''}
//                 ${data.verdict}
//             </span>`;


//         document.getElementById(
//             'resultSimilarity'
//         ).textContent =
//             data.similarity;


//         document.getElementById(
//             'resultRegions'
//         ).textContent =
//             data.regions_analyzed;


//         document.getElementById(
//             'compareOriginal'
//         ).src =
//             data.original_image_url;


//         document.getElementById(
//             'compareCaptured'
//         ).src =
//             data.captured_image_url;


//         card.style.display =
//             'block';


//         requestAnimationFrame(() => {

//             const fill =
//                 document.getElementById(
//                     'resultMeterFill'
//                 );


//             fill.classList.add(
//                 verdictClass
//             );


//             fill.style.width =
//                 `${Math.min(
//                     100,
//                     data.similarity
//                 )}%`;
//         });
//     }

// })();

(() => {
    const lookupError = document.getElementById('lookupError');
    const lookupLoading = document.getElementById('lookupLoading');
    const productInfo = document.getElementById('productInfo');

    let product = null;
    let capturedFile = null;

    // -----------------------------------------------------------
    // Show error message
    // -----------------------------------------------------------

    function showLookupError(msg) {
        lookupError.textContent = msg;
        lookupError.classList.add('show');

        if (lookupLoading) {
            lookupLoading.style.display = 'none';
        }
    }

    // -----------------------------------------------------------
    // Load product information
    // -----------------------------------------------------------

    fetch(`/api/product/${encodeURIComponent(PRODUCT_ID)}`)
        .then(response => {

            if (!response.ok) {
                throw new Error("Product request failed");
            }

            return response.json();
        })

        .then(data => {

            if (!data.ok) {

                showLookupError(
                    data.error ||
                    'This product could not be found on the ledger.'
                );

                return;
            }

            product = data.product;

            document.getElementById(
                'originalPreview'
            ).src = product.original_image_path;

            document.getElementById(
                'infoName'
            ).textContent = product.name;

            document.getElementById(
                'infoManufacturer'
            ).textContent = product.manufacturer;

            document.getElementById(
                'infoOnChain'
            ).textContent =
                data.on_chain
                    ? 'Confirmed on ledger'
                    : 'Not found on ledger';

            lookupLoading.style.display = 'none';

            productInfo.style.display = 'block';
        })

        .catch(error => {

            console.error(
                "Product lookup error:",
                error
            );

            showLookupError(
                'Could not reach the server. Please try again.'
            );
        });

    // -----------------------------------------------------------
    // Image upload elements
    // -----------------------------------------------------------

    const capturedInput =
        document.getElementById('capturedImage');

    const capturedPreview =
        document.getElementById('capturedPreview');

    const analyzeBtn =
        document.getElementById('analyzeBtn');

    // -----------------------------------------------------------
    // When customer selects an image
    // -----------------------------------------------------------

    capturedInput.addEventListener(
        'change',
        () => {

            const file =
                capturedInput.files[0];

            if (!file) {
                return;
            }

            capturedFile = file;

            capturedPreview.src =
                URL.createObjectURL(file);

            capturedPreview.style.display =
                'block';

            analyzeBtn.disabled = false;
        }
    );

    // -----------------------------------------------------------
    // Analysis animation
    // -----------------------------------------------------------

    const stepEls =
        Array.from(
            document.querySelectorAll('.l-step')
        );

    function animateSteps() {

        let i = 0;

        stepEls.forEach(el => {
            el.classList.remove(
                'active',
                'done'
            );
        });

        return new Promise(resolve => {

            const advance = () => {

                if (i > 0) {

                    stepEls[
                        i - 1
                    ].classList.add('done');
                }

                if (i >= stepEls.length) {

                    resolve();

                    return;
                }

                stepEls[i].classList.add(
                    'active'
                );

                i++;

                setTimeout(
                    advance,
                    650
                );
            };

            advance();
        });
    }

    // -----------------------------------------------------------
    // Analyze button
    // -----------------------------------------------------------

    analyzeBtn.addEventListener(
        'click',
        async () => {

            if (!capturedFile) {

                showLookupError(
                    'Please select a product image.'
                );

                return;
            }

            document.getElementById(
                'lookupCard'
            ).style.display = 'none';

            document.getElementById(
                'analyzingCard'
            ).style.display = 'block';

            const fd = new FormData();

            fd.append(
                'captured_image',
                capturedFile
            );

            try {

                console.log(
                    "Starting AI verification..."
                );

                // Start animation
                animateSteps();

                console.log(
                    "Sending image to Flask..."
                );

                // Send image to Flask
                const response = await fetch(
                    `/api/verify/${encodeURIComponent(PRODUCT_ID)}`,
                    {
                        method: 'POST',
                        body: fd
                    }
                );

                console.log(
                    "Flask response received:",
                    response.status
                );

                if (!response.ok) {

                    throw new Error(
                        `Server returned ${response.status}`
                    );
                }

                const data =
                    await response.json();

                console.log(
                    "Verification result:",
                    data
                );

                document.getElementById(
                    'analyzingCard'
                ).style.display = 'none';

                if (!data.ok) {

                    document.getElementById(
                        'lookupCard'
                    ).style.display = 'block';

                    showLookupError(
                        data.error ||
                        'Verification failed.'
                    );

                    return;
                }

                // Display result
                renderResult(data);

            } catch (error) {

                console.error(
                    "Verification error:",
                    error
                );

                document.getElementById(
                    'analyzingCard'
                ).style.display = 'none';

                document.getElementById(
                    'lookupCard'
                ).style.display = 'block';

                // Updated error message
                showLookupError(
                    'Verification failed. Please try again.'
                );
            }
        }
    );

    // -----------------------------------------------------------
    // Display verification result
    // -----------------------------------------------------------

    function renderResult(data) {

        const verdictClass =
            data.verdict.toLowerCase();

        const card =
            document.getElementById(
                'resultCard'
            );

        document.getElementById(
            'resultProductName'
        ).textContent =
            data.product_name;

        document.getElementById(
            'resultEyebrow'
        ).textContent =
            data.manufacturer;

        const badge =
            document.getElementById(
                'resultVerdictBadge'
            );

        const icons = {

            authentic:
                '&#10003;',

            suspicious:
                '&#9888;',

            counterfeit:
                '&#10005;'
        };

        badge.innerHTML =
            `<span class="verdict-badge ${verdictClass}">
                ${icons[verdictClass] || ''}
                ${data.verdict}
            </span>`;

        document.getElementById(
            'resultSimilarity'
        ).textContent =
            data.similarity;

        document.getElementById(
            'resultRegions'
        ).textContent =
            data.regions_analyzed;

        document.getElementById(
            'compareOriginal'
        ).src =
            data.original_image_url;

        document.getElementById(
            'compareCaptured'
        ).src =
            data.captured_image_url;

        card.style.display =
            'block';

        requestAnimationFrame(() => {

            const fill =
                document.getElementById(
                    'resultMeterFill'
                );

            fill.classList.add(
                verdictClass
            );

            fill.style.width =
                `${Math.min(
                    100,
                    data.similarity
                )}%`;
        });
    }

})();
