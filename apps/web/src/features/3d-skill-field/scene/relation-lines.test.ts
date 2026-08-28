import { describe, expect, it } from "vitest";
import * as THREE from "three";
import { relationLineEndpoints } from "./relation-lines";

function screenPoint(point: THREE.Vector3, camera: THREE.PerspectiveCamera) {
  const projected = point.clone().project(camera);
  return new THREE.Vector2((projected.x * 0.5 + 0.5) * 1280, (-projected.y * 0.5 + 0.5) * 720);
}

describe("relation endpoint anchoring", () => {
  it.each([0, 90, 180, 270])("keeps the intentional endpoint gap close to the star and label anchor at %i degrees", (angle) => {
    const source = new THREE.Vector3(0, 0, 0);
    const target = new THREE.Vector3(3.2, 0.65, 1.1);
    const endpoints = relationLineEndpoints(source, target, 1.18, 0.34);
    const radians = THREE.MathUtils.degToRad(angle);
    const camera = new THREE.PerspectiveCamera(44, 1280 / 720, 0.1, 100);
    camera.position.set(Math.sin(radians) * 22, 3, Math.cos(radians) * 22);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
    // Skill star and DOM label both project the same rendered position. The line ends just outside that star.
    expect(screenPoint(source, camera).distanceTo(screenPoint(endpoints.start, camera))).toBeLessThanOrEqual(30);
    expect(screenPoint(target, camera).distanceTo(screenPoint(endpoints.end, camera))).toBeLessThan(22);
  });
});
