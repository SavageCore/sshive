# Maintainer: SavageCore
pkgname=sshive
pkgver=0.0.0
pkgrel=1
pkgdesc="Your hive of SSH connections - A modern SSH connection manager"
arch=('any')
url="https://github.com/SavageCore/sshive"
license=('MIT')
depends=('python' 'pyside6' 'python-qtawesome' 'python-packaging' 'python-platformdirs' 'python-nanoid')
makedepends=('python-build' 'python-installer' 'python-hatchling')

_local_repo=0
if [[ -d "$startdir/.git" && -f "$startdir/pyproject.toml" ]]; then
    _local_repo=1
fi

if [[ "${SSHIVE_USE_REMOTE_SOURCE:-0}" == "1" ]]; then
    _local_repo=0
fi

if (( _local_repo )); then
    source=()
    sha256sums=()
else
    source=("sshive-$pkgver.tar.gz::https://github.com/SavageCore/sshive/archive/v$pkgver.tar.gz")
    sha256sums=('SKIP')
fi

_build_root="$srcdir/$pkgname-$pkgver"
if (( _local_repo )); then
    _build_root="$startdir"
fi

build() {
    cd "$_build_root"
    python -m build --wheel --no-isolation
}

package() {
    cd "$_build_root"
    python -m installer --destdir="$pkgdir" dist/*.whl
    install -Dm644 scripts/sshive.desktop "$pkgdir/usr/share/applications/sshive.desktop"
    install -Dm644 sshive/resources/icon.png "$pkgdir/usr/share/icons/hicolor/512x512/apps/sshive.png"
}
