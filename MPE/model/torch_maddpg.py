from ray.rllib.models.modelv2 import ModelV2
from ray.rllib.models.tf.tf_modelv2 import TFModelV2
from ray.rllib.models.tf.fcnet import FullyConnectedNetwork
from ray.rllib.models.torch.misc import SlimFC
from ray.rllib.models.torch.torch_modelv2 import TorchModelV2
from ray.rllib.models.torch.fcnet import FullyConnectedNetwork as TorchFC
from ray.rllib.utils.annotations import override
from ray.rllib.utils.framework import try_import_tf, try_import_torch


tf1, tf, tfv = try_import_tf()
torch, nn = try_import_torch()

class DDPGCentralizedCriticModel(TorchModelV2, nn.Module):
    """Multi-agent model that implements a centralized VF."""

    def __init__(self, obs_space, action_space, num_outputs, model_config,
                 name):
        TorchModelV2.__init__(self, obs_space, action_space, num_outputs,
                              model_config, name)
        nn.Module.__init__(self)

        # Base of the model
        self.model = TorchFC(obs_space, action_space, num_outputs,
                             model_config, name)
        self.n_agents = model_config["custom_model_config"]["agent_num"]


        # Central VF maps (obs, opp_obs, opp_act) -> vf_pred
        self.obs_size = obs_space.shape[0]
        self.action_size = action_space.shape[0]
        input_size = self.obs_size * self.n_agents + self.action_size * (self.n_agents - 1)
        self.central_vf = nn.Sequential(
            SlimFC(input_size, 16, activation_fn=nn.Tanh),
            SlimFC(16, 1),
        )

    @override(ModelV2)
    def forward(self, input_dict, state, seq_lens):
        model_out, _ = self.model(input_dict, state, seq_lens)
        return model_out, []

    def central_value_function(self, obs, opponent_obs, opponent_actions):

        input_ = torch.cat([
            obs, torch.flatten(opponent_obs, start_dim=1),
            torch.flatten(opponent_actions, start_dim=1)], 1)

        return torch.reshape(self.central_vf(input_), [-1])
