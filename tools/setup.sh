#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

foundry_version=v1.4.4
openzeppelin_revision=a5445b0afb8b350417b6e6ab3160554967bc151f
forge_std_revision=77041d2ce690e692d6e03cc812b57d1ddaa4d505

for required_command in curl tar git install; do
    command -v "$required_command" >/dev/null || {
        printf 'Falta el comando requerido: %s\n' "$required_command" >&2
        exit 1
    }
done

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
    printf 'Este instalador requiere Linux x86_64.\n' >&2
    exit 1
fi

mkdir -p .tools/bin lib
setup_tmp="$(mktemp -d "$project_dir/.tools/setup.XXXXXX")"
trap 'rm -rf -- "$setup_tmp"' EXIT

if [[ ! -x .tools/bin/forge ]] || ! .tools/bin/forge --version | head -n 1 | grep -q '1\.4\.4'; then
    archive="foundry_${foundry_version}_linux_amd64.tar.gz"
    curl --fail --location --connect-timeout 10 --max-time 120 \
        "https://github.com/foundry-rs/foundry/releases/download/${foundry_version}/${archive}" \
        --output "$setup_tmp/$archive"
    tar -xzf "$setup_tmp/$archive" -C "$setup_tmp" forge cast anvil chisel
    for binary in forge cast anvil chisel; do
        install -m 755 "$setup_tmp/$binary" ".tools/bin/$binary"
    done
fi

install_dependency() {
    local name="$1" repository="$2" revision="$3"
    if [[ -d "lib/$name" ]]; then
        if [[ "$(git -C "lib/$name" rev-parse HEAD)" != "$revision" ]] || \
            [[ -n "$(git -C "lib/$name" status --porcelain)" ]]; then
            printf 'Revisar lib/%s: revisión distinta o cambios locales.\n' "$name" >&2
            return 1
        fi
        return
    fi
    git init --quiet "$setup_tmp/$name"
    git -C "$setup_tmp/$name" remote add origin "$repository"
    git -C "$setup_tmp/$name" fetch --depth 1 origin "$revision"
    git -C "$setup_tmp/$name" checkout --quiet --detach FETCH_HEAD
    mv "$setup_tmp/$name" "lib/$name"
}

install_dependency openzeppelin-contracts https://github.com/OpenZeppelin/openzeppelin-contracts.git "$openzeppelin_revision"
install_dependency forge-std https://github.com/foundry-rs/forge-std.git "$forge_std_revision"

.tools/bin/forge --version
.tools/bin/cast --version
.tools/bin/anvil --version
printf 'Entorno instalado. Ejecutar: export PATH="$PWD/.tools/bin:$PATH"\n'
