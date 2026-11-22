const Matter = require('matter-js');
const { createCanvas } = require('canvas');
const ffmpeg = require('fluent-ffmpeg');
const fs = require('fs');
const path = require('path');

// Set ffmpeg path
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;
ffmpeg.setFfmpegPath(ffmpegPath);

// Configuration - 1080p as requested but optimized for speed
const WIDTH = 1920;
const HEIGHT = 1080;
const DURATION = 45; // seconds
const FPS = 24; // Reduced from 30 for faster rendering
const TOTAL_FRAMES = DURATION * FPS;
const OUTPUT_FILE = '/workspace/funny_sphere.mp4';
const TEMP_DIR = '/workspace/frames';

// Ensure temp directory exists
if (!fs.existsSync(TEMP_DIR)) {
  fs.mkdirSync(TEMP_DIR, { recursive: true });
}

// Create canvas
const canvas = createCanvas(WIDTH, HEIGHT);
const ctx = canvas.getContext('2d');

// Set up physics engine with simpler settings
const engine = Matter.Engine.create({ 
  enableSleeping: true,
  gravity: { x: 0, y: 1 }
});
const world = engine.world;

// Simplified funny sphere - fewer segments for faster simulation
function createFunnySphere(x, y, radius) {
  const group = Matter.Body.nextGroup(true);
  const bodies = [];
  const numSegments = 6; // Reduced from 8-10
  
  // Create circular segments
  for (let i = 0; i < numSegments; i++) {
    const angle = (i / numSegments) * Math.PI * 2;
    const px = x + Math.cos(angle) * radius * 0.7;
    const py = y + Math.sin(angle) * radius * 0.7;
    const body = Matter.Bodies.circle(px, py, radius / 3, {
      friction: 0.1,
      restitution: 0.8,
      frictionAir: 0.02,
      density: 0.001,
      collisionFilter: { group: group },
      sleepThreshold: 0.1
    });
    bodies.push(body);
    Matter.World.add(world, body);
  }
  
  // Connect them in a circle
  for (let i = 0; i < numSegments; i++) {
    const bodyA = bodies[i];
    const bodyB = bodies[(i + 1) % numSegments];
    const constraint = Matter.Constraint.create({
      bodyA: bodyA,
      bodyB: bodyB,
      length: Matter.Vector.magnitude(Matter.Vector.sub(bodyB.position, bodyA.position)),
      stiffness: 0.1,
      damping: 0.1
    });
    Matter.World.add(world, constraint);
  }
  
  // Connect to center
  const center = Matter.Bodies.circle(x, y, radius / 5, {
    isStatic: false,
    density: 0.0001,
    collisionFilter: { group: group },
    sleepThreshold: 0.1
  });
  Matter.World.add(world, center);
  
  for (let i = 0; i < numSegments; i++) {
    const constraint = Matter.Constraint.create({
      bodyA: center,
      bodyB: bodies[i],
      length: radius * 0.7,
      stiffness: 0.05,
      damping: 0.1
    });
    Matter.World.add(world, constraint);
  }
  
  return { bodies, center };
}

// Create boundaries
const ground = Matter.Bodies.rectangle(WIDTH / 2, HEIGHT - 20, WIDTH, 40, { 
  isStatic: true,
  friction: 0.5
});
const leftWall = Matter.Bodies.rectangle(20, HEIGHT / 2, 40, HEIGHT, { isStatic: true });
const rightWall = Matter.Bodies.rectangle(WIDTH - 20, HEIGHT / 2, 40, HEIGHT, { isStatic: true });
const ceiling = Matter.Bodies.rectangle(WIDTH / 2, 20, WIDTH, 40, { isStatic: true });

Matter.World.add(world, [ground, leftWall, rightWall, ceiling]);

// Create funny spheres
const spheres = [];
for (let i = 0; i < 2; i++) { // Reduced from 3
  const sphere = createFunnySphere(
    WIDTH / 2 + (i - 0.5) * 200,
    HEIGHT / 3,
    50 + i * 15
  );
  spheres.push(sphere);
}

// Add fewer platforms
for (let i = 0; i < 3; i++) { // Reduced from 5
  const platform = Matter.Bodies.rectangle(
    WIDTH / 3 + i * 200,
    HEIGHT / 2 + i * 100,
    70,
    15,
    {
      isStatic: false,
      restitution: 0.9,
      friction: 0.1,
      chamfer: { radius: 5 },
      sleepThreshold: 0.1
    }
  );
  Matter.World.add(world, platform);
}

async function start() {
  console.log('Starting funny sphere animation...');
  console.log(`Resolution: ${WIDTH}x${HEIGHT}`);
  console.log(`Duration: ${DURATION}s at ${FPS}fps = ${TOTAL_FRAMES} frames\n`);

  const startTime = Date.now();

  // Generate all frames
  for (let frame = 0; frame < TOTAL_FRAMES; frame++) {
    // Update physics with smaller time steps
    const delta = 1000 / FPS;
    const steps = Math.ceil(delta / 16);
    for (let i = 0; i < steps; i++) {
      Matter.Engine.update(engine, delta / steps);
    }
    
    // Add objects less frequently
    if (frame % 80 === 0) {
      const shape = Matter.Bodies.polygon(
        Math.random() * WIDTH,
        30,
        Math.floor(3 + Math.random() * 4),
        15 + Math.random() * 15,
        {
          restitution: 0.7,
          friction: 0.1,
          density: 0.001,
          sleepThreshold: 0.1
        }
      );
      Matter.World.add(world, shape);
    }
    
    // Draw frame - simplified rendering
    ctx.fillStyle = '#000011';
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
    
    // Draw all bodies
    Matter.Composite.allBodies(world).forEach((body, index) => {
      if (body.isStatic) {
        ctx.fillStyle = 'rgba(50, 50, 80, 0.3)';
        ctx.strokeStyle = 'rgba(100, 100, 150, 0.5)';
        ctx.lineWidth = 1;
      } else {
        const speed = Matter.Vector.magnitude(body.velocity);
        const hue = (frame * 0.03 + index * 0.2 + speed * 0.02) % 1;
        ctx.fillStyle = `hsl(${hue * 360}, 90%, 60%)`;
        ctx.strokeStyle = `hsl(${hue * 360}, 100%, 85%)`;
        ctx.lineWidth = 1;
      }
      
      if (body.circleRadius) {
        ctx.beginPath();
        ctx.arc(body.position.x, body.position.y, body.circleRadius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        
        // Add face only to main sphere
        if (body === spheres[0]?.center) {
          const eyeOffset = body.circleRadius * 0.5;
          const eyeRadius = body.circleRadius * 0.2;
          
          ctx.fillStyle = '#FFFFFF';
          ctx.beginPath();
          ctx.arc(body.position.x - eyeOffset, body.position.y - eyeOffset, eyeRadius, 0, Math.PI * 2);
          ctx.arc(body.position.x + eyeOffset, body.position.y - eyeOffset, eyeRadius, 0, Math.PI * 2);
          ctx.fill();
          
          ctx.fillStyle = '#000000';
          const pupilRadius = eyeRadius * 0.6;
          const pupilXOffset = Math.cos(frame * 0.2) * eyeRadius * 0.4;
          ctx.beginPath();
          ctx.arc(body.position.x - eyeOffset + pupilXOffset, body.position.y - eyeOffset, pupilRadius, 0, Math.PI * 2);
          ctx.arc(body.position.x + eyeOffset - pupilXOffset, body.position.y - eyeOffset, pupilRadius, 0, Math.PI * 2);
          ctx.fill();
          
          ctx.strokeStyle = '#FF0000';
          ctx.lineWidth = body.circleRadius * 0.15;
          ctx.beginPath();
          ctx.arc(body.position.x, body.position.y + eyeOffset * 0.8, body.circleRadius * 0.7, Math.PI * 0.2, Math.PI * 0.8);
          ctx.stroke();
        }
      } else {
        ctx.beginPath();
        ctx.moveTo(body.vertices[0].x, body.vertices[0].y);
        for (let i = 1; i < body.vertices.length; i++) {
          ctx.lineTo(body.vertices[i].x, body.vertices[i].y);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }
    });
    
    // Draw constraints
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1;
    Matter.Composite.allConstraints(world).forEach(constraint => {
      if (constraint.bodyA && constraint.bodyB) {
        ctx.beginPath();
        ctx.moveTo(constraint.bodyA.position.x, constraint.bodyA.position.y);
        ctx.lineTo(constraint.bodyB.position.x, constraint.bodyB.position.y);
        ctx.stroke();
      }
    });
    
    // Save frame
    const frameFile = path.join(TEMP_DIR, `frame_${String(frame).padStart(5, '0')}.png`);
    const out = fs.createWriteStream(frameFile);
    const stream = canvas.createPNGStream();
    stream.pipe(out);
    
    await new Promise((resolve) => {
      out.on('finish', resolve);
    });
    
    // Progress
    if (frame % 50 === 0) {
      const elapsed = (Date.now() - startTime) / 1000;
      const fpsActual = frame / elapsed;
      const remaining = ((TOTAL_FRAMES - frame) / fpsActual) / 60;
      console.log(`Frame ${frame}/${TOTAL_FRAMES} (${Math.floor(frame / FPS)}s) - ${Math.round((frame / TOTAL_FRAMES) * 100)}% - ${fpsActual.toFixed(1)}fps - ${remaining.toFixed(1)}min remaining`);
    }
  }
  
  console.log('\nAll frames rendered. Encoding video...');
  
  // Encode to MP4
  return new Promise((resolve, reject) => {
    ffmpeg()
      .input(path.join(TEMP_DIR, 'frame_%05d.png'))
      .inputFPS(FPS)
      .size(`${WIDTH}x${HEIGHT}`)
      .videoCodec('libx264')
      .outputOptions([
        '-pix_fmt', 'yuv420p',
        '-preset', 'ultrafast',
        '-crf', '28',
        '-t', String(DURATION)
      ])
      .on('progress', progress => {
        console.log(`Encoding: ${Math.round(progress.percent)}% done`);
      })
      .on('end', () => {
        console.log('Video encoded!');
        
        // Cleanup
        for (let frame = 0; frame < TOTAL_FRAMES; frame++) {
          const frameFile = path.join(TEMP_DIR, `frame_${String(frame).padStart(5, '0')}.png`);
          try { fs.unlinkSync(frameFile); } catch (e) {}
        }
        fs.rmdirSync(TEMP_DIR, { recursive: true });
        
        const stats = fs.statSync(OUTPUT_FILE);
        const totalTime = (Date.now() - startTime) / 1000;
        console.log(`\n✓ Video created: ${OUTPUT_FILE}`);
        console.log(`  Size: ${Math.round(stats.size / 1024 / 1024 * 100) / 100} MB`);
        console.log(`  Duration: ${DURATION}s`);
        console.log(`  Resolution: ${WIDTH}x${HEIGHT}`);
        console.log(`  Total time: ${Math.round(totalTime)} seconds`);
        resolve();
      })
      .on('error', err => {
        console.error('Encoding error:', err);
        reject(err);
      })
      .save(OUTPUT_FILE);
  });
}

console.log('Starting...\n');
start().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
