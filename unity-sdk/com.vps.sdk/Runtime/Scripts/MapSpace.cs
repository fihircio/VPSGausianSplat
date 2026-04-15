using UnityEngine;

namespace VPS.SDK
{
    /// <summary>
    /// The MapSpace represents the coordinate origin of the VPS Map.
    /// All virtual content anchored to the VPS map should be children of this transform.
    /// </summary>
    public class MapSpace : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Camera arCamera;
        [SerializeField] private VPSClient vpsClient;

        [Header("Settings")]
        [SerializeField] private bool alignOnLocalization = true;
        [Range(0, 1)]
        [SerializeField] private float alignmentSmoothing = 1.0f; // 1.0 = instant alignment

        public VPSClient Client => vpsClient;

        private void OnEnable()
        {
            if (vpsClient != null)
            {
                vpsClient.OnLocalizationSuccess += HandleLocalization;
            }
        }

        private void OnDisable()
        {
            if (vpsClient != null)
            {
                vpsClient.OnLocalizationSuccess -= HandleLocalization;
            }
        }

        private void Start()
        {
            if (arCamera == null) arCamera = Camera.main;
            if (vpsClient == null) vpsClient = GetComponent<VPSClient>();
        }

        private void HandleLocalization(LocalizationResponse response)
        {
            if (!alignOnLocalization) return;

            // 1. Get the camera's pose in Map Space from VPS
            Vector3 camPosInMap = response.GetUnityPosition();
            Quaternion camRotInMap = response.GetUnityRotation();

            // 2. Get the current camera pose in Unity World space
            Vector3 camPosInUnity = arCamera.transform.position;
            Quaternion camRotInUnity = arCamera.transform.rotation;

            // 3. Align MapSpace to Unity World
            // We want UnityWorld_Cam = MapSpace_World * Map_Cam
            // Therefore: MapSpace_World = UnityWorld_Cam * Inverse(Map_Cam)
            
            Matrix4x4 cameraWorldMatrix = Matrix4x4.TRS(camPosInUnity, camRotInUnity, Vector3.one);
            Matrix4x4 camInMapMatrix = Matrix4x4.TRS(camPosInMap, camRotInMap, Vector3.one);
            
            Matrix4x4 newMapSpaceMatrix = cameraWorldMatrix * camInMapMatrix.inverse;

            Vector3 targetPosition = newMapSpaceMatrix.GetColumn(3);
            Quaternion targetRotation = Quaternion.LookRotation(
                newMapSpaceMatrix.GetColumn(2),
                newMapSpaceMatrix.GetColumn(1)
            );

            // Apply alignment
            if (alignmentSmoothing >= 1.0f)
            {
                transform.position = targetPosition;
                transform.rotation = targetRotation;
            }
            else
            {
                transform.position = Vector3.Lerp(transform.position, targetPosition, alignmentSmoothing);
                transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, alignmentSmoothing);
            }

            Debug.Log($"MapSpace Aligned! Confidence: {response.confidence:P1}, Inliers: {response.inliers}");
        }

        /// <summary>
        /// Explicitly triggers a localization request through the connected client.
        /// Useful for UI buttons or interval-based scripts.
        /// </summary>
        public void RequestLocalization(Texture2D frame = null)
        {
            if (vpsClient == null) return;
            
            if (frame != null)
                vpsClient.Localize(frame);
            else
                Debug.LogWarning("RequestLocalization called with null frame. Ensure you pass a camera frame.");
        }
    }
}
