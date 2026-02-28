#!/bin/bash

################################################################################
# Script: create_inference_profile.sh
# Descripción: Crear Application Inference Profile en AWS Bedrock
# Uso: ./create_inference_profile.sh
################################################################################

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
REGION="eu-west-1"
ACCOUNT_ID="701055077130"

################################################################################
# Función: Crear Inference Profile
################################################################################
create_inference_profile() {
    local profile_name=$1
    local team=$2
    local application=$3
    local model_id=$4
    local environment=${5:-"Production"}
    
    echo -e "${YELLOW}Creando inference profile: ${profile_name}${NC}"
    
    # Construir ARN del modelo base
    local model_arn="arn:aws:bedrock:${REGION}:${ACCOUNT_ID}:inference-profile/${model_id}"
    
    # Crear el profile
    aws bedrock create-inference-profile \
      --inference-profile-name "${profile_name}" \
      --model-source "{
        \"copyFrom\": \"${model_arn}\"
      }" \
      --tags "[
        {
          \"key\": \"Project\",
          \"value\": \"${team}\"
        },
        {
          \"key\": \"Component\",
          \"value\": \"${application}\"
        },
        {
          \"key\": \"CostCenter\",
          \"value\": \"Engineering\"
        },
        {
          \"key\": \"Environment\",
          \"value\": \"${environment}\"
        },
        {
          \"key\": \"Model\",
          \"value\": \"Claude-Sonnet-4.5\"
        },
        {
          \"key\": \"Team\",
          \"value\": \"${team}\"
        },
        {
          \"key\": \"Application\",
          \"value\": \"${application}\"
        }
      ]" \
      --region ${REGION}
}

################################################################################
# Función: Listar Inference Profiles
################################################################################
list_inference_profiles() {
    echo -e "${YELLOW}Listando inference profiles existentes...${NC}"
    aws bedrock list-inference-profiles --region ${REGION} --output table
}

################################################################################
# Función: Obtener detalles de un profile
################################################################################
get_inference_profile() {
    local profile_id=$1
    echo -e "${YELLOW}Obteniendo detalles del profile: ${profile_id}${NC}"
    aws bedrock get-inference-profile \
      --inference-profile-identifier "${profile_id}" \
      --region ${REGION} \
      --output json | jq .
}

################################################################################
# Función: Eliminar Inference Profile
################################################################################
delete_inference_profile() {
    local profile_id=$1
    echo -e "${RED}Eliminando inference profile: ${profile_id}${NC}"
    aws bedrock delete-inference-profile \
      --inference-profile-identifier "${profile_id}" \
      --region ${REGION}
}

################################################################################
# EJEMPLOS DE USO
################################################################################

# Ejemplo 1: Crear profile para Cline
# Nomenclatura: {team}-{model}-{application}-profile
# create_inference_profile \
#   "lcs-claude_sonnet_4_5-sdlc-gen-cline-profile" \
#   "lcs-sdlc-gen-group" \
#   "Cline" \
#   "eu.anthropic.claude-sonnet-4-5-20250929-v1:0" \
#   "Production"

# Ejemplo 2: Crear profile para otra aplicación
# create_inference_profile \
#   "lcs-claude_sonnet_4_5-sdlc-gen-myapp-profile" \
#   "lcs-sdlc-gen-group" \
#   "MyApp" \
#   "eu.anthropic.claude-sonnet-4-5-20250929-v1:0" \
#   "Development"

################################################################################
# MENÚ INTERACTIVO
################################################################################

show_menu() {
    echo ""
    echo "=================================="
    echo "  Bedrock Inference Profile Manager"
    echo "=================================="
    echo "1. Crear nuevo inference profile"
    echo "2. Listar inference profiles"
    echo "3. Ver detalles de un profile"
    echo "4. Eliminar inference profile"
    echo "5. Salir"
    echo "=================================="
}

main() {
    while true; do
        show_menu
        read -p "Selecciona una opción: " option
        
        case $option in
            1)
                echo ""
                read -p "Nombre del profile (ej: lcs-claude_sonnet_4_5-sdlc-gen-cline-profile): " profile_name
                read -p "Team (ej: lcs-sdlc-gen-group): " team
                read -p "Aplicación (ej: Cline): " application
                read -p "Model ID (ej: eu.anthropic.claude-sonnet-4-5-20250929-v1:0): " model_id
                read -p "Environment (Production/Development) [Production]: " environment
                environment=${environment:-Production}
                
                create_inference_profile "$profile_name" "$team" "$application" "$model_id" "$environment"
                
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}✓ Inference profile creado exitosamente${NC}"
                else
                    echo -e "${RED}✗ Error creando inference profile${NC}"
                fi
                ;;
            2)
                list_inference_profiles
                ;;
            3)
                echo ""
                read -p "Profile ID o ARN: " profile_id
                get_inference_profile "$profile_id"
                ;;
            4)
                echo ""
                read -p "Profile ID o ARN a eliminar: " profile_id
                read -p "¿Estás seguro? (yes/no): " confirm
                if [ "$confirm" = "yes" ]; then
                    delete_inference_profile "$profile_id"
                    echo -e "${GREEN}✓ Inference profile eliminado${NC}"
                else
                    echo "Operación cancelada"
                fi
                ;;
            5)
                echo "Saliendo..."
                exit 0
                ;;
            *)
                echo -e "${RED}Opción inválida${NC}"
                ;;
        esac
        
        echo ""
        read -p "Presiona Enter para continuar..."
    done
}

################################################################################
# EJECUCIÓN
################################################################################

# Si se pasan argumentos, ejecutar directamente
if [ $# -gt 0 ]; then
    case $1 in
        create)
            create_inference_profile "$2" "$3" "$4" "$5" "$6"
            ;;
        list)
            list_inference_profiles
            ;;
        get)
            get_inference_profile "$2"
            ;;
        delete)
            delete_inference_profile "$2"
            ;;
        *)
            echo "Uso: $0 {create|list|get|delete} [args...]"
            echo ""
            echo "Ejemplos:"
            echo "  $0 create 'profile-name' 'team' 'app' 'model-id' 'env'"
            echo "  $0 list"
            echo "  $0 get 'profile-id'"
            echo "  $0 delete 'profile-id'"
            exit 1
            ;;
    esac
else
    # Modo interactivo
    main
fi
