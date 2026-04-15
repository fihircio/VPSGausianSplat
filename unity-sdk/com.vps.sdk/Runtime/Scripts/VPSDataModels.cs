using System;
using UnityEngine;

namespace VPS.SDK
{
    [Serializable]
    public class LocalizationRequest
    {
        public string scene_id;
        // query_image is sent as binary multipart
    }

    [Serializable]
    public class LocalizationResponse
    {
        public float[] position;
        public float[] rotation;
        public int inliers;
        public float confidence;

        public Vector3 GetUnityPosition()
        {
            return CoordinateConverter.CVToUnityPosition(CoordinateConverter.ArrayToVector3(position));
        }

        public Quaternion GetUnityRotation()
        {
            return CoordinateConverter.CVToUnityRotation(CoordinateConverter.ArrayToQuaternion(rotation));
        }
    }

    [Serializable]
    public class SceneModel
    {
        public string id;
        public string name;
        public string status;
        public string created_at;
    }
}
