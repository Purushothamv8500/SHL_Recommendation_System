document.addEventListener('DOMContentLoaded', () => {
    // Initialize shader background
    const canvas = document.getElementById('shader-background');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (!gl) {
        console.warn('WebGL not supported, falling back to static background');
        canvas.style.display = 'none';
        return;
    }

    // Handle canvas resize
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        gl.viewport(0, 0, canvas.width, canvas.height);
    }

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // Vertex shader program - basic pass-through
    const vsSource = `
        attribute vec4 aVertexPosition;
        attribute vec2 aTextureCoord;

        varying highp vec2 vTextureCoord;

        void main(void) {
            gl_Position = aVertexPosition;
            vTextureCoord = aTextureCoord;
        }
    `;

    // Fragment shader program - creates a colorful, animated gradient
    const fsSource = `
        precision mediump float;
        varying highp vec2 vTextureCoord;
        
        uniform float uTime;
        uniform vec2 uResolution;
        uniform bool uIsLightMode;

        // Noise function
        float noise(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
        }

        // Simplex-like 2D noise
        vec2 smoothNoise(vec2 st) {
            vec2 f = fract(st);
            vec2 i = floor(st);
            
            // Four corners
            float a = noise(i);
            float b = noise(i + vec2(1.0, 0.0));
            float c = noise(i + vec2(0.0, 1.0));
            float d = noise(i + vec2(1.0, 1.0));

            // Smooth interpolation
            vec2 u = f * f * (3.0 - 2.0 * f);
            
            // Mix
            float nx = mix(a, b, u.x);
            float ny = mix(c, d, u.x);
            return vec2(nx, mix(nx, ny, u.y));
        }

        void main() {
            // Normalized coordinates
            vec2 st = gl_FragCoord.xy / uResolution.xy;
            st.x *= uResolution.x / uResolution.y;
            
            // Time-based movement
            float t = uTime * 0.1;
            
            // Different noise layers
            vec2 noise1 = smoothNoise(st * 3.0 + t);
            vec2 noise2 = smoothNoise(st * 6.0 - t * 0.3);
            vec2 noise3 = smoothNoise(st * 9.0 + t * 0.5);
            
            // Combined noise for movement
            vec2 noisePos = st + vec2(
                sin(noise1.x * 2.0 * 3.14159 + t) * 0.05,
                cos(noise1.y * 2.0 * 3.14159 + t) * 0.05
            );
            
            // Distance from center
            vec2 center = vec2(0.5, 0.5);
            float dist = distance(noisePos, center);
            
            // Create gradients with noise
            float r = smoothNoise(noisePos * 1.0 + t * 0.2).x;
            float g = smoothNoise(noisePos * 1.5 - t * 0.3).y;
            float b = smoothNoise(noisePos * 2.0 + t * 0.4).x;
            
            // Customize colors for light/dark mode
            if (uIsLightMode) {
                // Light mode - subtle pastels
                vec3 color1 = vec3(0.95, 0.95, 0.95); // Light background
                vec3 color2 = vec3(0.99, 0.90, 0.85); // Soft peach
                vec3 color3 = vec3(1.0, 0.85, 0.8);   // Light orange
                
                // Blend colors
                vec3 finalColor = mix(
                    mix(color1, color2, r * 0.3), 
                    color3, 
                    g * 0.2
                );
                
                // Add subtle highlight
                finalColor += vec3(1.0, 0.6, 0.4) * b * 0.05;
                
                gl_FragColor = vec4(finalColor, 1.0);
            } else {
                // Dark mode - deep gradients (updated to match new color scheme)
                vec3 color1 = vec3(0.149, 0.149, 0.141);  // #262624
                vec3 color2 = vec3(0.188, 0.188, 0.18); // #30302e
                vec3 color3 = vec3(0.165, 0.165, 0.155);   // Midpoint between the two
                
                // Blend colors
                vec3 finalColor = mix(
                    mix(color1, color2, r * 0.5), 
                    color3, 
                    g * 0.3
                );
                
                // Add orange/red highlights
                finalColor += vec3(0.7, 0.3, 0.1) * b * 0.08;
                
                gl_FragColor = vec4(finalColor, 1.0);
            }
        }
    `;

    // Initialize shader program
    function initShaderProgram(gl, vsSource, fsSource) {
        const vertexShader = loadShader(gl, gl.VERTEX_SHADER, vsSource);
        const fragmentShader = loadShader(gl, gl.FRAGMENT_SHADER, fsSource);

        // Create the shader program
        const shaderProgram = gl.createProgram();
        gl.attachShader(shaderProgram, vertexShader);
        gl.attachShader(shaderProgram, fragmentShader);
        gl.linkProgram(shaderProgram);

        // Check if it linked successfully
        if (!gl.getProgramParameter(shaderProgram, gl.LINK_STATUS)) {
            console.error('Unable to initialize the shader program: ' + gl.getProgramInfoLog(shaderProgram));
            return null;
        }

        return shaderProgram;
    }

    // Load a shader
    function loadShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);

        // Check if it compiled successfully
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error('An error occurred compiling the shaders: ' + gl.getShaderInfoLog(shader));
            gl.deleteShader(shader);
            return null;
        }

        return shader;
    }

    // Create shader program
    const shaderProgram = initShaderProgram(gl, vsSource, fsSource);

    // Collect shader attributes and uniforms
    const programInfo = {
        program: shaderProgram,
        attribLocations: {
            vertexPosition: gl.getAttribLocation(shaderProgram, 'aVertexPosition'),
            textureCoord: gl.getAttribLocation(shaderProgram, 'aTextureCoord'),
        },
        uniformLocations: {
            time: gl.getUniformLocation(shaderProgram, 'uTime'),
            resolution: gl.getUniformLocation(shaderProgram, 'uResolution'),
            isLightMode: gl.getUniformLocation(shaderProgram, 'uIsLightMode'),
        },
    };

    // Create vertices for a full-screen quad
    const positions = [
        -1.0, -1.0,
         1.0, -1.0,
         1.0,  1.0,
        -1.0,  1.0,
    ];

    const textureCoordinates = [
        0.0, 0.0,
        1.0, 0.0,
        1.0, 1.0,
        0.0, 1.0,
    ];

    const indices = [
        0, 1, 2,
        0, 2, 3,
    ];

    // Create buffers
    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.STATIC_DRAW);

    const textureCoordBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, textureCoordBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(textureCoordinates), gl.STATIC_DRAW);

    const indexBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indexBuffer);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(indices), gl.STATIC_DRAW);

    // Buffers for rendering
    const buffers = {
        position: positionBuffer,
        textureCoord: textureCoordBuffer,
        indices: indexBuffer,
    };

    // Draw the scene
    let startTime = Date.now();
    let previousIsLightMode = !document.body.classList.contains('light-mode');

    function render() {
        // Calculate time in seconds
        const now = Date.now();
        const elapsed = (now - startTime) / 1000;

        // Check if light mode changed
        const isLightMode = document.body.classList.contains('light-mode');
        if (isLightMode !== previousIsLightMode) {
            previousIsLightMode = isLightMode;
        }

        // Clear the canvas
        gl.clearColor(0.0, 0.0, 0.0, 1.0);
        gl.clear(gl.COLOR_BUFFER_BIT);

        // Use our shader program
        gl.useProgram(programInfo.program);

        // Set position attribute
        gl.bindBuffer(gl.ARRAY_BUFFER, buffers.position);
        gl.vertexAttribPointer(
            programInfo.attribLocations.vertexPosition,
            2,
            gl.FLOAT,
            false,
            0,
            0
        );
        gl.enableVertexAttribArray(programInfo.attribLocations.vertexPosition);

        // Set texture coordinates attribute
        gl.bindBuffer(gl.ARRAY_BUFFER, buffers.textureCoord);
        gl.vertexAttribPointer(
            programInfo.attribLocations.textureCoord,
            2,
            gl.FLOAT,
            false,
            0,
            0
        );
        gl.enableVertexAttribArray(programInfo.attribLocations.textureCoord);

        // Set indices
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffers.indices);

        // Set uniforms
        gl.uniform1f(programInfo.uniformLocations.time, elapsed);
        gl.uniform2f(programInfo.uniformLocations.resolution, canvas.width, canvas.height);
        gl.uniform1i(programInfo.uniformLocations.isLightMode, isLightMode ? 1 : 0);

        // Draw the quad
        gl.drawElements(gl.TRIANGLES, 6, gl.UNSIGNED_SHORT, 0);

        // Request next frame
        requestAnimationFrame(render);
    }

    // Start the rendering loop
    render();

    // Enhance the table animations
    const resultsTable = document.getElementById('results-tbody');
    if (resultsTable) {
        // Modify the displayResults function
        const originalDisplayResults = window.displayResults;
        if (typeof originalDisplayResults === 'function') {
            window.displayResults = function(data) {
                originalDisplayResults(data);
                
                // Add staggered animations to table rows
                const rows = resultsTable.querySelectorAll('tr');
                rows.forEach((row, index) => {
                    setTimeout(() => {
                        row.classList.add('show');
                    }, 100 * index);
                });
            };
        }
    }
}); 