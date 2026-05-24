// HLSL Shader Model 6.6 — Xbox Direct3D 12 Ultimate Rigid/Smooth Skinning Shader
// Target GPU   : AMD RDNA2 (Xbox Series X/S, Unified Memory Architecture)
// Pipeline     : ZKAEDI Casino Jackpot Fleet — 18 rigged GLB assets
//
// ── CONSTRAINTS (must be enforced by the CPU-side pipeline) ─────────────────
//   1. BoneCount must be uploaded before draw (SkinningBuffer, b1).
//   2. JointSpace SRV must be bound to t0 with exactly BoneCount entries.
//   3. Supports both uniform and non-uniform scale keyframes via InverseTransposeMatrix.
// ────────────────────────────────────────────────────────────────────────────

// 🔱 D3D12 ULTIMATE ROOT SIGNATURE SERIALIZATION
// Embeds the hardware descriptor table layout directly inside the shader binary
// to enable zero-overhead CPU boundary validation and automatic pipeline binding.
#define ZkaediXboxRootSig \
    "RootFlags(ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT), " \
    "CBV(b0, visibility = SHADER_VISIBILITY_VERTEX), " \
    "CBV(b1, visibility = SHADER_VISIBILITY_VERTEX), " \
    "SRV(t0, visibility = SHADER_VISIBILITY_VERTEX)"

struct VertexInput
{
    float3 Position      : POSITION;
    float3 Normal        : NORMAL;
    float2 TexCoord      : TEXCOORD0;
    uint4  JointIndices  : BLENDINDICES0; // First 4 joint indices
    float4 JointWeights  : BLENDWEIGHT0;  // First 4 weights
    uint4  JointIndices1 : BLENDINDICES1; // Second 4 joint indices (8-slider support)
    float4 JointWeights1 : BLENDWEIGHT1;  // Second 4 weights (8-slider support)
};

struct PixelInput
{
    float4 SVPosition  : SV_POSITION;
    float3 WorldNormal : NORMAL;
    float2 TexCoord    : TEXCOORD0;
};

// 128-byte aligned joint transform supporting non-uniform scales
struct JointTransform
{
    float4x4 WorldMatrix;
    float4x4 InverseTransposeMatrix;
};

// b0 — Camera Constant Buffer
cbuffer CameraBuffer : register(b0)
{
    float4x4 ViewProjection;
};

// b1 — Per-draw skinning metadata constant buffer
cbuffer SkinningBuffer : register(b1)
{
    uint BoneCount;  // Actual bones bound in JointSpace this draw.
                     // Caps the joint index clamp; prevents OOB SRV reads
                     // for assets with fewer than 127 bones in the rig.
};

// t0 — Bindless Structured Buffer of Joint matrices
StructuredBuffer<JointTransform> JointSpace : register(t0);

// ─────────────────────────────────────────────────────────────────────────────
[RootSignature(ZkaediXboxRootSig)]
PixelInput VS_XboxMain(VertexInput input)
{
    PixelInput output;

    // 🛡️ Hardware index boundary clamp (compiles to UMin operations, no branches)
    uint jointIndex0 = min(input.JointIndices.x, min(BoneCount - 1u, 127u));

#if defined(ZKAEDI_SMOOTH_SKINNING)
    // 🔱 SMOOTH 8-WEIGHT LBS PATH (8-slider mechanical coordination)
    uint jointIndex1 = min(input.JointIndices.y, min(BoneCount - 1u, 127u));
    uint jointIndex2 = min(input.JointIndices.z, min(BoneCount - 1u, 127u));
    uint jointIndex3 = min(input.JointIndices.w, min(BoneCount - 1u, 127u));
    uint jointIndex4 = min(input.JointIndices1.x, min(BoneCount - 1u, 127u));
    uint jointIndex5 = min(input.JointIndices1.y, min(BoneCount - 1u, 127u));
    uint jointIndex6 = min(input.JointIndices1.z, min(BoneCount - 1u, 127u));
    uint jointIndex7 = min(input.JointIndices1.w, min(BoneCount - 1u, 127u));

    float4x4 skinMatrix0 = JointSpace[jointIndex0].WorldMatrix;
    float4x4 skinMatrix1 = JointSpace[jointIndex1].WorldMatrix;
    float4x4 skinMatrix2 = JointSpace[jointIndex2].WorldMatrix;
    float4x4 skinMatrix3 = JointSpace[jointIndex3].WorldMatrix;
    float4x4 skinMatrix4 = JointSpace[jointIndex4].WorldMatrix;
    float4x4 skinMatrix5 = JointSpace[jointIndex5].WorldMatrix;
    float4x4 skinMatrix6 = JointSpace[jointIndex6].WorldMatrix;
    float4x4 skinMatrix7 = JointSpace[jointIndex7].WorldMatrix;

    float4x4 normalMatrix0 = JointSpace[jointIndex0].InverseTransposeMatrix;
    float4x4 normalMatrix1 = JointSpace[jointIndex1].InverseTransposeMatrix;
    float4x4 normalMatrix2 = JointSpace[jointIndex2].InverseTransposeMatrix;
    float4x4 normalMatrix3 = JointSpace[jointIndex3].InverseTransposeMatrix;
    float4x4 normalMatrix4 = JointSpace[jointIndex4].InverseTransposeMatrix;
    float4x4 normalMatrix5 = JointSpace[jointIndex5].InverseTransposeMatrix;
    float4x4 normalMatrix6 = JointSpace[jointIndex6].InverseTransposeMatrix;
    float4x4 normalMatrix7 = JointSpace[jointIndex7].InverseTransposeMatrix;

    // Normalize weights dynamically to maintain volume preservation across all 8 sliders
    float weightSum = input.JointWeights.x + input.JointWeights.y + input.JointWeights.z + input.JointWeights.w +
                      input.JointWeights1.x + input.JointWeights1.y + input.JointWeights1.z + input.JointWeights1.w;
                      
    float w0 = weightSum > 0.0f ? input.JointWeights.x / weightSum : 1.0f;
    float w1 = weightSum > 0.0f ? input.JointWeights.y / weightSum : 0.0f;
    float w2 = weightSum > 0.0f ? input.JointWeights.z / weightSum : 0.0f;
    float w3 = weightSum > 0.0f ? input.JointWeights.w / weightSum : 0.0f;
    float w4 = weightSum > 0.0f ? input.JointWeights1.x / weightSum : 0.0f;
    float w5 = weightSum > 0.0f ? input.JointWeights1.y / weightSum : 0.0f;
    float w6 = weightSum > 0.0f ? input.JointWeights1.z / weightSum : 0.0f;
    float w7 = weightSum > 0.0f ? input.JointWeights1.w / weightSum : 0.0f;

    // Linear matrix blend (fused multiply-adds on RDNA2 vector units)
    float4x4 skinMatrix = skinMatrix0 * w0 + skinMatrix1 * w1 + skinMatrix2 * w2 + skinMatrix3 * w3 +
                          skinMatrix4 * w4 + skinMatrix5 * w5 + skinMatrix6 * w6 + skinMatrix7 * w7;
                          
    float4x4 normalMatrix = normalMatrix0 * w0 + normalMatrix1 * w1 + normalMatrix2 * w2 + normalMatrix3 * w3 +
                            normalMatrix4 * w4 + normalMatrix5 * w5 + normalMatrix6 * w6 + normalMatrix7 * w7;
#else
    // ⚡ HIGH-OCCUPANCY RIGID PATH (Zero deformation mechanical rotating elements)
    // Avoids redundant memory fetches and registers, maximizing GPU Wavefront occupancy.
    float4x4 skinMatrix = JointSpace[jointIndex0].WorldMatrix;
    float4x4 normalMatrix = JointSpace[jointIndex0].InverseTransposeMatrix;
#endif

    // ── Position transform ────────────────────────────────────────────────
    float4 worldPos    = mul(float4(input.Position, 1.0f), skinMatrix);
    output.SVPosition  = mul(worldPos, ViewProjection);

    // ── Normal transform ──────────────────────────────────────────────────
    // Transform normals using the blended inverse-transpose normal matrix to support non-uniform scaling
    output.WorldNormal = normalize(mul((float3x3)normalMatrix, input.Normal));

    output.TexCoord = input.TexCoord;

    return output;
}
