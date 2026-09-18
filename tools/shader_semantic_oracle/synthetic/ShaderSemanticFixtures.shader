Shader "ShaderSemanticOracle/SyntheticSurface"
{
    Properties
    {
        _MainTex ("Base Texture", 2D) = "white" {}
        _Color ("Base Color", Color) = (1,1,1,1)
        _BumpMap ("Normal", 2D) = "bump" {}
        _EmissionMap ("Emission", 2D) = "black" {}
        _Cutoff ("Alpha Cutoff", Range(0,1)) = 0.5
    }
    SubShader { Tags { "RenderType"="Opaque" } Pass { } }
}
