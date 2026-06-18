using System;
using UnityEngine;

namespace VPS.SDK
{
    [Serializable]
    public class LocalizationRequest
    {
        public string scene_id;
    }

    [Serializable]
    public class LocalizationResponse
    {
        public float[] position;
        public float[] rotation;
        public int inliers;
        public float confidence;
        public string hint_used;

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
    public class MultiFrameLocalizationResponse
    {
        public float[] position;
        public float[] rotation;
        public int inliers;
        public float confidence;
        public int frames_used;
        public float[] frame_confidences;
        public string hint_used;

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

    [Serializable]
    public class AgentPoseUpdate
    {
        public string type;
        public string agent_id;
        public string name;
        public string role;
        public float[] position;
        public float[] rotation;
    }

    [Serializable]
    public class SpatialHintOptions
    {
        public float[] hintPosition;
        public float hintRadius = 25f;
        public float[] hintFloorHeight;
        public string geoHint;
    }
}
