import pytest
import os
import platform
import sh
import yaml

from validators import (
    validate_dns_dashboard,
    validate_dashboard_ingress,
    validate_storage,
    validate_ingress,
    validate_ambassador,
    validate_gpu,
    validate_istio,
    validate_knative,
    validate_registry,
    validate_forward,
    validate_metrics_server,
    validate_fluentd,
    validate_inaccel,
    validate_jaeger,
    validate_keda,
    validate_linkerd,
    validate_rbac,
    validate_cilium,
    validate_multus,
    validate_metallb_config,
    validate_prometheus,
    validate_traefik,
    validate_coredns_config,
    validate_portainer,
    validate_openfaas,
    validate_openebs,
    validate_kata,
    validate_argocd,
)
from utils import (
    microk8s_enable,
    wait_for_pod_state,
    wait_for_namespace_termination,
    microk8s_disable,
    microk8s_reset,
    is_container,
)
from subprocess import PIPE, STDOUT, CalledProcessError, check_call, run, check_output


class TestAddons(object):
    @pytest.fixture(scope="session", autouse=True)
    def clean_up(self):
        """
        Clean up after a test
        """
        yield
        microk8s_reset()

    @pytest.mark.skipif(
        platform.machine() != "s390x",
        reason="This test is for the limited set of addons s390x has",
    )
    def test_basic_s390x(self):
        """
        Sets up and tests dashboard, dns, storage, registry, ingress, metrics server.

        """
        ip_ranges = "8.8.8.8,1.1.1.1"
        print("Enabling DNS")
        microk8s_enable("{}:{}".format("dns", ip_ranges), timeout_insec=500)
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        print("Validating DNS config")
        validate_coredns_config(ip_ranges)

    @pytest.mark.skipif(platform.machine() == "s390x", reason="Not available on s390x")
    def test_basic(self):
        """
        Sets up and tests dashboard, dns, storage, registry, ingress, metrics server.

        """
        ip_ranges = "8.8.8.8,1.1.1.1"
        print("Enabling DNS")
        microk8s_enable("{}:{}".format("dns", ip_ranges), timeout_insec=500)
        wait_for_pod_state("", "kube-system", "running", label="k8s-app=kube-dns")
        print("Validating DNS config")
        validate_coredns_config(ip_ranges)
        print("Enabling ingress")
        microk8s_enable("ingress")
        print("Enabling metrics-server")
        microk8s_enable("metrics-server")
        print("Validating ingress")
        validate_ingress()
        print("Disabling ingress")
        microk8s_disable("ingress")
        print("Enabling dashboard")
        microk8s_enable("dashboard")
        print("Validating dashboard")
        validate_dns_dashboard()
        print("Enabling dashboard-ingress")
        microk8s_enable("dashboard-ingress")
        print("Validating dashboard-ingress")
        validate_dashboard_ingress()
        print("Disabling dashboard-ingress")
        microk8s_disable("dashboard-ingress")
        print("Disabling metrics-server")
        microk8s_disable("metrics-server")
        print("Disabling dashboard")
        microk8s_disable("dashboard")
        """
        We would disable DNS here but this freezes any terminating pods.
        We let microk8s reset to do the cleanup.
        print("Disabling DNS")
        microk8s_disable("dns")
        """

    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping FPGA tests as we are under time pressure",
    )
    @pytest.mark.skipif(
        os.environ.get("TEST_FPGA") != "True",
        reason="Skipping FPGA because TEST_FPGA is not set",
    )
    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="FPGA tests are only relevant in x86 architectures",
    )
    def test_inaccel(self):
        """
        Sets up inaccel.

        """
        try:
            print("Enabling inaccel")
            microk8s_enable("inaccel")
        except CalledProcessError:
            # Failed to enable addon. Skip the test.
            print("Could not enable inaccel support")
            return
        validate_inaccel()
        print("Disable inaccel")
        microk8s_disable("inaccel")

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Istio tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping istio and knative tests as we are under time pressure",
    )
    def test_knative_istio(self):
        """
        Sets up and validate istio.

        """
        print("Enabling Knative and Istio")
        microk8s_enable("knative")
        print("Validating Istio")
        validate_istio()
        print("Validating Knative")
        validate_knative()
        print("Disabling Knative")
        microk8s_disable("knative")
        wait_for_namespace_termination("knative-serving", timeout_insec=600)
        print("Disabling Istio")
        microk8s_disable("istio")

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Fluentd, prometheus, jaeger tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping jaeger, prometheus and fluentd tests as we are under time pressure",
    )
    def test_monitoring_addons(self):
        """
        Test jaeger, prometheus and fluentd.

        """
        print("Enabling fluentd")
        microk8s_enable("fluentd")
        print("Enabling jaeger")
        microk8s_enable("jaeger")
        print("Validating the Jaeger operator")
        validate_jaeger()
        print("Validating the Fluentd")
        validate_fluentd()
        print("Disabling jaeger")
        microk8s_disable("jaeger")
        print("Disabling fluentd")
        microk8s_disable("fluentd")

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Cilium tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(is_container(), reason="Cilium tests are skipped in containers")
    def test_cilium(self):
        """
        Sets up and validates Cilium.
        """
        print("Enabling Cilium")
        run(
            "/snap/bin/microk8s.enable cilium".split(),
            stdout=PIPE,
            input=b"N\n",
            stderr=STDOUT,
            check=True,
        )
        print("Validating Cilium")
        validate_cilium()
        print("Disabling Cilium")
        microk8s_disable("cilium")
        microk8s_reset()

    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping Linkerd tests as we are under time pressure",
    )
    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Linkerd test is available for amd64",
    )
    @pytest.mark.skipif(platform.machine() == "s390x", reason="Not available on s390x")
    def test_linkerd(self):
        """
        Sets up and validate linkerd

        """
        print("Enabling Linkerd")
        microk8s_enable("linkerd")
        print("Validating Linkerd")
        validate_linkerd()
        print("Disabling Linkerd")
        microk8s_disable("linkerd")

    @pytest.mark.skip("disabling the test while we work on a 1.20 release")
    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Ambassador tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping ambassador tests as we are under time pressure",
    )
    def test_ambassador(self):
        """
        Test Ambassador.

        """
        print("Enabling Ambassador")
        microk8s_enable("ambassador")
        print("Validating ambassador")
        validate_ambassador()
        print("Disabling Ambassador")
        microk8s_disable("ambassador")

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Multus tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping multus tests as we are under time pressure",
    )
    def test_multus(self):
        """
        Sets up and validates Multus.
        """
        print("Enabling Multus")
        microk8s_enable("multus")
        print("Validating Multus")
        validate_multus()
        print("Disabling Multus")
        microk8s_disable("multus")

    @pytest.mark.skipif(platform.machine() == "s390x", reason="Not available on s390x")
    def test_portainer(self):
        """
        Sets up and validates Portainer.
        """
        print("Enabling Portainer")
        microk8s_enable("portainer")
        print("Validating Portainer")
        validate_portainer()
        print("Disabling Portainer")
        microk8s_disable("portainer")

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="OpenFaaS tests are only relevant in x86 architectures",
    )
    def test_openfaas(self):
        """
        Sets up and validates OpenFaaS.
        """
        print("Enabling openfaas")
        microk8s_enable("openfaas")
        print("Validating openfaas")
        validate_openfaas()
        print("Disabling openfaas")
        microk8s_disable("openfaas")

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="ArgoCD tests are only relevant in x86 architectures",
    )
    def test_argocd(self):
        """
        Sets up and validates ArgoCD.
        """
        print("Enabling argocd")
        microk8s_enable("argocd")
        print("Validating argocd")
        validate_argocd()
        print("Disabling argocd")
        microk8s_disable("argocd")

    @pytest.mark.skipif(platform.machine() == "s390x", reason="Not available on s390x")
    def test_traefik(self):
        """
        Sets up and validates traefik.
        """
        print("Enabling traefik")
        microk8s_enable("traefik")
        print("Validating traefik")
        validate_traefik()
        print("Disabling traefik")
        microk8s_disable("traefik")

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="KEDA tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        os.environ.get("UNDER_TIME_PRESSURE") == "True",
        reason="Skipping KEDA tests as we are under time pressure",
    )
    def test_keda(self):
        """
        Sets up and validates keda.
        """
        print("Enabling keda")
        microk8s_enable("keda")
        print("Validating keda")
        validate_keda()
        print("Disabling keda")
        microk8s_disable("keda")

    @pytest.mark.skipif(
        platform.machine() == "s390x", reason="OpenEBS is not available on s390x"
    )
    def test_openebs(self):
        """
        Sets up and validates openebs.
        """
        print("Enabling OpenEBS")
        try:
            check_output("systemctl is-enabled iscsid".split()).strip().decode("utf8")
            microk8s_enable("openebs")
            print("Validating OpenEBS")
            validate_openebs()
            print("Disabling OpenEBS")
            microk8s_disable("openebs:force")
        except CalledProcessError:
            print("Nothing to do, since iscsid is not available")
            return

    @pytest.mark.skipif(
        platform.machine() != "x86_64",
        reason="Kata tests are only relevant in x86 architectures",
    )
    @pytest.mark.skipif(
        is_container(), reason="Kata tests are only possible on real hardware"
    )
    def test_kata(self):
        """
        Sets up and validates kata.
        """
        print("Enabling kata")
        microk8s_enable("kata")
        print("Validating Kata")
        validate_kata()
        print("Disabling kata")
        microk8s_disable("kata")
