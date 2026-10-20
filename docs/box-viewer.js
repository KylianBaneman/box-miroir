// Visionneuse 3D de la box miroir. Se monte dans l'élément #box-viewer (taille gérée en CSS).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';

const container = document.getElementById('box-viewer');
const HDRI_ROT = THREE.MathUtils.degToRad(225); // orientation de la ville reflétée (même valeur que box_miroir.py)
const Y = new THREE.Vector3(0, 1, 0);

// Fond transparent : c'est le CSS de la page qui donne la couleur
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.AgXToneMapping;
container.appendChild(renderer.domElement);

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
camera.position.set(5.5, 1.6, 7).applyAxisAngle(Y, HDRI_ROT);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 1.3, 0);
controls.enableDamping = true;
controls.enablePan = false;
controls.minDistance = 4;
controls.maxDistance = 20;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.6;
controls.addEventListener('start', () => (controls.autoRotate = false));

const [env, gltf] = await Promise.all([
  new RGBELoader().loadAsync('potsdamer_platz_2k.hdr'),
  new GLTFLoader().loadAsync('box.glb'),
]);
// La ville sert uniquement d'éclairage et de reflet dans les miroirs, elle n'est pas affichée
env.mapping = THREE.EquirectangularReflectionMapping;
scene.environment = env;
scene.environmentIntensity = 2.2; // éclaircit la porte et le laiton (ciel couvert assez sombre)

// Miroirs nets : réflexion pure sur une cubemap 1024 (les matériaux PBR passent par PMREM, qui floute)
const sharp = new THREE.WebGLCubeRenderTarget(1024).fromEquirectangularTexture(renderer, env);
const mirror = new THREE.MeshBasicMaterial({ color: 0xeeeeee, envMap: sharp.texture });
gltf.scene.traverse((o) => {
  if (o.material?.name === 'Miroir') o.material = mirror;
});
gltf.scene.rotation.y = HDRI_ROT;
scene.add(gltf.scene);

new ResizeObserver(() => {
  const { clientWidth: w, clientHeight: h } = container;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}).observe(container);

renderer.setAnimationLoop(() => {
  controls.update();
  renderer.render(scene, camera);
});
